"""Small lab adapter: measurements only; Kubernetes HPA performs all scaling."""
import base64
import json
import math
import os
import ssl
import tempfile
import threading
import time
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request
from werkzeug.serving import make_server

METRIC_NAME = 'api_requests_per_minute'
TARGET = 50
MIN_REPLICAS = 1
MAX_REPLICAS = 5
WINDOW = 60
API_SERVICE = 'v1beta1.external.metrics.k8s.io'


def timestamp():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


class RollingRequests:
    """A real rolling 60-second window, plus per-Pod totals since adapter start."""
    def __init__(self, clock=time.monotonic, wall_clock=time.time):
        self.clock = clock
        self.wall_clock = wall_clock
        self.events = deque()
        self.seen = {}
        self.totals = Counter()
        self.endpoint_totals = Counter()
        self.lock = threading.Lock()

    def _prune(self, now):
        # Delayed retries may arrive out of order, so filter instead of popleft.
        self.events = deque(e for e in self.events if e['at'] > now - WINDOW)
        self.seen = {key: at for key, at in self.seen.items() if at > now - 3600}

    def record(self, data):
        event_id = data.get('id')
        pod = data.get('pod')
        latency = data.get('latency_ms')
        path = data.get('path', '/api/request')
        if (not isinstance(event_id, str) or not event_id or len(event_id) > 100
                or not isinstance(pod, str) or not pod or len(pod) > 253
                or not isinstance(latency, (int, float)) or isinstance(latency, bool)
                or not math.isfinite(latency) or latency < 0 or latency > 60000
                or path not in {'/api/projects', '/api/analyze', '/api/request'}):
            raise ValueError('id, pod, latency_ms 값을 확인하세요.')
        now = self.clock()
        completed = data.get('completed_at')
        at = now
        if completed is not None:
            try:
                date = datetime.fromisoformat(completed.replace('Z', '+00:00'))
                if date.tzinfo is None:
                    raise ValueError()
                # Preserve original completion time when a failed delivery is retried.
                age = max(0, self.wall_clock() - date.timestamp())
                at = now - age
            except (ValueError, AttributeError, TypeError):
                raise ValueError('completed_at은 시간대가 포함된 ISO 시각이어야 합니다.')
        with self.lock:
            self._prune(now)
            if event_id in self.seen:
                return False
            self.seen[event_id] = now
            self.totals[pod] += 1
            self.endpoint_totals[path] += 1
            if at > now - WINDOW:
                self.events.append({'at': at, 'pod': pod, 'path': path, 'latency_ms': latency})
        return True

    def snapshot(self):
        now = self.clock()
        with self.lock:
            self._prune(now)
            by_pod = defaultdict(list)
            by_endpoint = defaultdict(list)
            for event in self.events:
                by_pod[event['pod']].append(event['latency_ms'])
                by_endpoint[event['path']].append(event['latency_ms'])
            pods = []
            for name, total in sorted(self.totals.items()):
                values = by_pod[name]
                pods.append({'name': name, 'requests_last_minute': len(values),
                             'total_requests': total,
                             'average_latency_ms': round(sum(values) / len(values), 2) if values else 0})
            values = [e['latency_ms'] for e in self.events]
            endpoints = []
            for path in ['/api/projects', '/api/analyze', '/api/request']:
                latencies = by_endpoint[path]
                endpoints.append({'path': path, 'requests_last_minute': len(latencies),
                                  'total_requests': self.endpoint_totals[path],
                                  'average_latency_ms': round(sum(latencies) / len(latencies), 2) if latencies else 0})
            return {'requests_last_minute': len(values), 'total_requests': sum(self.totals.values()),
                    'average_latency_ms': round(sum(values) / len(values), 2) if values else 0,
                    'recommended_replicas': min(MAX_REPLICAS, max(MIN_REPLICAS, math.ceil(len(values) / TARGET))),
                    'pods': pods, 'endpoints': endpoints, 'metrics_updated_at': timestamp(), 'window_seconds': WINDOW}


class KubernetesReader:
    """Read actual cluster objects with the mounted ServiceAccount and verified TLS."""
    def __init__(self):
        account = Path('/var/run/secrets/kubernetes.io/serviceaccount')
        self.token_path = account / 'token'
        self.ca_path = account / 'ca.crt'
        self.namespace = os.environ.get('POD_NAMESPACE', 'default')
        self.base = 'https://' + os.environ.get('KUBERNETES_SERVICE_HOST', 'kubernetes.default.svc')
        self.base += ':' + os.environ.get('KUBERNETES_SERVICE_PORT_HTTPS', '443')

    def request(self, path, method='GET', data=None):
        token = self.token_path.read_text(encoding='utf-8').strip()
        headers = {'Authorization': 'Bearer ' + token}
        if data is not None:
            headers['Content-Type'] = 'application/merge-patch+json'
        body = json.dumps(data).encode('utf-8') if data is not None else None
        req = Request(self.base + path, data=body, headers=headers, method=method)
        context = ssl.create_default_context(cafile=str(self.ca_path))
        with urlopen(req, context=context, timeout=2) as response:
            return json.load(response)

    def get(self, path):
        return self.request(path)

    def objects(self):
        namespace = quote(self.namespace, safe='')
        deployment = self.get(f'/apis/apps/v1/namespaces/{namespace}/deployments/api')
        pods = self.get(f'/api/v1/namespaces/{namespace}/pods?labelSelector=app%3Dapi')
        hpa = self.get(f'/apis/autoscaling/v2/namespaces/{namespace}/horizontalpodautoscalers/api')
        return deployment, pods, hpa


store = RollingRequests()
reader = KubernetesReader()
internal = Flask('metrics_internal')
external = Flask('metrics_external')
internal.json.ensure_ascii = False
internal.config['MAX_CONTENT_LENGTH'] = 16 * 1024


def register_certificate(ca_pem, client=None, attempts=30, pause=time.sleep):
    """Trust this Pod's new certificate without creating cluster resources or disabling TLS."""
    client = client or reader
    path = '/apis/apiregistration.k8s.io/v1/apiservices/' + API_SERVICE
    for attempt in range(attempts):
        try:
            service = client.get(path)
            metadata = service.get('metadata', {})
            spec = service.get('spec', {})
            endpoint = spec.get('service', {})
            if (metadata.get('labels', {}).get('app.kubernetes.io/part-of') != 'week6-lab'
                    or endpoint.get('namespace') != 'default'
                    or endpoint.get('name') != 'metrics'
                    or endpoint.get('port') != 8443
                    or spec.get('group') != GROUP
                    or spec.get('version') != VERSION
                    or spec.get('insecureSkipTLSVerify', False)):
                raise ValueError('week6 실습용 APIService 설정을 확인하세요.')
            client.request(path, method='PATCH', data={
                # A concurrent edit must be rechecked before its trust is changed.
                'metadata': {'resourceVersion': metadata['resourceVersion']},
                'spec': {'caBundle': base64.b64encode(ca_pem).decode('ascii')},
            })
            print('요청량 지표 연결 준비 완료', flush=True)
            return
        except HTTPError as error:
            if error.code not in {404, 409, 429, 500, 502, 503, 504}:
                raise
            last_error = error
        except OSError as error:
            last_error = error
        if attempt + 1 < attempts:
            pause(2)
    raise RuntimeError('요청량 지표 연결 실패: k8s 설정과 metrics 로그를 확인하세요.') from last_error


@internal.get('/health')
def health():
    return jsonify(status='ok')


@internal.post('/internal/record')
def record():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='JSON 요청이 필요합니다.'), 400
    try:
        recorded = store.record(data)
    except ValueError as error:
        return jsonify(error=str(error)), 400
    return jsonify(status='ok', recorded=recorded)


@internal.get('/internal/dashboard')
def dashboard():
    result = store.snapshot()
    try:
        deployment, pod_list, hpa = reader.objects()
    except (OSError, ValueError):
        return jsonify(error='Kubernetes 배포 상태를 읽지 못했습니다.',
                       metrics_updated_at=timestamp()), 503
    observed = {p['name']: p for p in result['pods']}
    live = []
    for pod in sorted(pod_list.get('items', []), key=lambda p: p['metadata']['name']):
        name = pod['metadata']['name']
        item = observed.pop(name, {'name': name, 'requests_last_minute': 0,
                                   'total_requests': 0, 'average_latency_ms': 0})
        conditions = pod.get('status', {}).get('conditions', [])
        item.update(ready=any(c['type'] == 'Ready' and c['status'] == 'True' for c in conditions),
                    phase=pod.get('status', {}).get('phase', 'Unknown'),
                    created_at=pod['metadata'].get('creationTimestamp'),
                    terminating='deletionTimestamp' in pod['metadata'])
        live.append(item)
    # Recently deleted Pods stay visible with their real measured requests.
    for item in observed.values():
        if item['requests_last_minute']:
            item.update(ready=False, phase='Deleted', created_at=None, terminating=False)
            live.append(item)
    status = deployment.get('status', {})
    hpa_status = hpa.get('status', {})
    # 변경 실습에서 HPA YAML의 실제 목표·범위를 읽습니다.
    # 읽지 못한 선택 값은 실습 기본값을 사용하며 원자료는 변경하지 않습니다.
    hpa_spec = hpa.get('spec', {})
    target = TARGET
    minimum = hpa_spec.get('minReplicas', MIN_REPLICAS)
    maximum = hpa_spec.get('maxReplicas', MAX_REPLICAS)
    for metric in hpa_spec.get('metrics', []):
        external_metric = metric.get('external', {})
        if external_metric.get('metric', {}).get('name') == METRIC_NAME:
            try:
                configured = float(external_metric.get('target', {}).get('averageValue', TARGET))
                if math.isfinite(configured) and configured > 0:
                    target = int(configured) if configured.is_integer() else configured
            except (ValueError, TypeError):
                pass
            break
    if (not isinstance(minimum, int) or not isinstance(maximum, int)
            or minimum < 0 or maximum < max(1, minimum)):
        minimum, maximum = MIN_REPLICAS, MAX_REPLICAS
    result.update(pods=live, desired_replicas=deployment['spec'].get('replicas', 1),
                  current_replicas=status.get('replicas', 0), ready_replicas=status.get('readyReplicas', 0),
                  current_average_requests_per_minute=round(result['requests_last_minute'] / status['replicas'], 2) if status.get('replicas', 0) else 0,
                  target_requests_per_minute=target,
                  recommended_replicas=min(maximum, max(minimum, math.ceil(result['requests_last_minute'] / target))),
                  autoscaler={'name': 'api', 'target_requests_per_minute': target,
                              'min_replicas': minimum, 'max_replicas': maximum,
                              'current_replicas': hpa_status.get('currentReplicas', 0),
                              'desired_replicas': hpa_status.get('desiredReplicas', 0),
                              'conditions': hpa_status.get('conditions', []),
                              'last_scale_time': hpa_status.get('lastScaleTime')})
    return jsonify(result)


GROUP = 'external.metrics.k8s.io'
VERSION = 'v1beta1'


def group_description():
    return {'name': GROUP, 'versions': [{'groupVersion': GROUP + '/' + VERSION, 'version': VERSION}],
            'preferredVersion': {'groupVersion': GROUP + '/' + VERSION, 'version': VERSION}}


@external.get('/health')
def external_health():
    return jsonify(status='ok')


@external.get('/apis')
def groups():
    return jsonify(kind='APIGroupList', apiVersion='v1', groups=[group_description()])


@external.get('/apis/external.metrics.k8s.io')
def group():
    return jsonify(kind='APIGroup', apiVersion='v1', **group_description())


@external.get('/apis/external.metrics.k8s.io/v1beta1')
def resources():
    return jsonify(kind='APIResourceList', apiVersion='v1', groupVersion=GROUP + '/' + VERSION,
                   resources=[{'name': METRIC_NAME, 'singularName': '', 'namespaced': True,
                               'kind': 'ExternalMetricValueList', 'verbs': ['get']}])


@external.get('/apis/external.metrics.k8s.io/v1beta1/namespaces/<namespace>/<metric>')
def external_metric(namespace, metric):
    if metric != METRIC_NAME or namespace != os.environ.get('POD_NAMESPACE', 'default'):
        return jsonify(kind='Status', apiVersion='v1', status='Failure', reason='NotFound', code=404), 404
    snapshot = store.snapshot()
    return jsonify(kind='ExternalMetricValueList', apiVersion=GROUP + '/' + VERSION,
                   metadata={}, items=[{'metricName': METRIC_NAME, 'metricLabels': {},
                                        'timestamp': snapshot['metrics_updated_at'],
                                        'windowSeconds': WINDOW,
                                        'value': str(snapshot['requests_last_minute'])}])


if __name__ == '__main__':
    from generate_certs import generate

    # Each single-replica metrics Pod owns fresh, short-lived TLS material.
    # Recreate deployment prevents two different serving certificates overlapping.
    with tempfile.TemporaryDirectory(prefix='week6-metrics-') as directory:
        generate(directory)
        files = Path(directory)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        tls.load_cert_chain(str(files / 'tls.crt'), str(files / 'tls.key'))
        register_certificate((files / 'ca.crt').read_bytes())
        secured = make_server('0.0.0.0', 8443, external, threaded=True, ssl_context=tls)
        threading.Thread(target=secured.serve_forever, daemon=True).start()
        internal.run(host='0.0.0.0', port=8000, debug=False)
