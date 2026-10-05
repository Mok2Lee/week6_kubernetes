import importlib.util
import base64
import io
import json
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location('metrics_lab', Path(__file__).parents[1] / 'metrics/app.py')
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)
cert_spec = importlib.util.spec_from_file_location('lab_certificates', Path(__file__).parents[1] / 'metrics/generate_certs.py')
certificates = importlib.util.module_from_spec(cert_spec)
cert_spec.loader.exec_module(certificates)


class CertificateBootstrapTests(unittest.TestCase):
    def api_service(self):
        return {'metadata': {'resourceVersion': '7', 'labels': {'app.kubernetes.io/part-of': 'week6-lab'}},
                'spec': {'group': 'external.metrics.k8s.io', 'version': 'v1beta1',
                         'service': {'namespace': 'default', 'name': 'metrics', 'port': 8443}}}

    def test_patches_only_named_api_service_and_preserves_verified_tls(self):
        client = MagicMock()
        client.get.return_value = self.api_service()
        metrics.register_certificate(b'new-ca', client=client)
        path = '/apis/apiregistration.k8s.io/v1/apiservices/v1beta1.external.metrics.k8s.io'
        client.request.assert_called_once_with(path, method='PATCH', data={
            'metadata': {'resourceVersion': '7'},
            'spec': {'caBundle': base64.b64encode(b'new-ca').decode('ascii')}})

    def test_refuses_foreign_service_or_insecure_configuration(self):
        for change in ['owner', 'namespace', 'name', 'port', 'group', 'version', 'insecure']:
            with self.subTest(change=change):
                obj = self.api_service()
                if change == 'owner':
                    obj['metadata']['labels']['app.kubernetes.io/part-of'] = 'other'
                elif change in {'namespace', 'name', 'port'}:
                    obj['spec']['service'][change] = 'other'
                elif change in {'group', 'version'}:
                    obj['spec'][change] = 'other'
                else:
                    obj['spec']['insecureSkipTLSVerify'] = True
                client = MagicMock()
                client.get.return_value = obj
                with self.assertRaises(ValueError):
                    metrics.register_certificate(b'new-ca', client=client)
                client.request.assert_not_called()

    def test_waits_for_manifest_and_rechecks_concurrent_change(self):
        client = MagicMock()
        client.get.side_effect = [HTTPError('https://cluster', 404, 'not yet applied', {}, None),
                                  self.api_service(), self.api_service()]
        client.request.side_effect = [HTTPError('https://cluster', 409, 'changed', {}, None), {}]
        pause = MagicMock()
        metrics.register_certificate(b'new-ca', client=client, attempts=3, pause=pause)
        self.assertEqual(client.get.call_count, 3)
        self.assertEqual(client.request.call_count, 2)
        self.assertEqual(pause.call_count, 2)

    def test_permission_failure_is_not_hidden_and_outage_is_bounded(self):
        client = MagicMock()
        denied = HTTPError('https://cluster', 403, 'forbidden', {}, None)
        client.get.side_effect = denied
        pause = MagicMock()
        with self.assertRaises(HTTPError):
            metrics.register_certificate(b'ca', client=client, pause=pause)
        pause.assert_not_called()
        client.get.side_effect = OSError('unavailable')
        with self.assertRaises(RuntimeError):
            metrics.register_certificate(b'ca', client=client, attempts=2, pause=pause)
        client.request.assert_not_called()
        pause.assert_called_once_with(2)

    def test_fresh_certificates_validate_for_service_and_keys_are_not_shared(self):
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization

        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            certificates.generate(first)
            certificates.generate(second)
            first, second = Path(first), Path(second)
            ca = x509.load_pem_x509_certificate((first / 'ca.crt').read_bytes())
            leaf = x509.load_pem_x509_certificate((first / 'tls.crt').read_bytes())
            leaf.verify_directly_issued_by(ca)
            names = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            self.assertIn('metrics.default.svc', names.get_values_for_type(x509.DNSName))
            key = serialization.load_pem_private_key((first / 'tls.key').read_bytes(), password=None)
            self.assertEqual(key.public_key().public_numbers(), leaf.public_key().public_numbers())
            self.assertNotEqual((first / 'tls.key').read_bytes(), (second / 'tls.key').read_bytes())
            self.assertNotEqual((first / 'ca.crt').read_bytes(), (second / 'ca.crt').read_bytes())
            self.assertEqual({p.name for p in first.iterdir()}, {'ca.crt', 'tls.crt', 'tls.key'})
            tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.load_cert_chain(str(first / 'tls.crt'), str(first / 'tls.key'))

    def test_api_patch_uses_service_account_and_cluster_ca_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            certificates.generate(directory)
            (directory / 'token').write_text('test-token', encoding='utf-8')
            reader = metrics.KubernetesReader()
            reader.token_path = directory / 'token'
            reader.ca_path = directory / 'ca.crt'
            response = MagicMock()
            response.__enter__.return_value = io.StringIO('{}')
            with patch.object(metrics, 'urlopen', return_value=response) as opener:
                reader.request('/apis/example', method='PATCH', data={'spec': {'caBundle': 'value'}})
            req = opener.call_args.args[0]
            context = opener.call_args.kwargs['context']
            self.assertEqual(req.method, 'PATCH')
            self.assertEqual(req.get_header('Authorization'), 'Bearer test-token')
            self.assertEqual(req.get_header('Content-type'), 'application/merge-patch+json')
            self.assertEqual(json.loads(req.data), {'spec': {'caBundle': 'value'}})
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.wall = 1000.0
        self.store = metrics.RollingRequests(clock=lambda: self.now, wall_clock=lambda: self.wall)

    def event(self, event_id, pod='api-1', path='/api/projects'):
        return {'id': event_id, 'pod': pod, 'path': path, 'latency_ms': 12.5}

    def test_window_aggregates_across_pods_and_exact_boundary_expires(self):
        self.store.record(self.event('a'))
        self.now = 101
        self.store.record(self.event('b', 'api-2', '/api/analyze'))
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['requests_last_minute'], 2)
        self.assertEqual(sum(p['requests_last_minute'] for p in snapshot['pods']), 2)
        self.assertEqual(sum(p['requests_last_minute'] for p in snapshot['endpoints']), 2)
        self.now = 160
        self.assertEqual(self.store.snapshot()['requests_last_minute'], 1)
        self.now = 161
        self.assertEqual(self.store.snapshot()['requests_last_minute'], 0)
        self.assertEqual(self.store.snapshot()['total_requests'], 2)

    def test_retry_is_deduplicated_and_old_completed_event_not_current_load(self):
        self.assertTrue(self.store.record(self.event('same')))
        self.assertFalse(self.store.record(self.event('same')))
        old = self.event('old')
        old['completed_at'] = '1970-01-01T00:15:00+00:00'  # 100 seconds before receipt.
        self.store.record(old)
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['requests_last_minute'], 1)
        self.assertEqual(snapshot['total_requests'], 2)

    def test_target_boundary_and_maximum(self):
        for i in range(251):
            self.store.record(self.event(str(i)))
            if i + 1 in {40, 50, 51, 100, 101, 120, 200, 201, 220, 250, 251}:
                expected = {40: 1, 50: 1, 51: 2, 100: 2, 101: 3, 120: 3, 200: 4, 201: 5, 220: 5, 250: 5, 251: 5}[i + 1]
                self.assertEqual(self.store.snapshot()['recommended_replicas'], expected)

    def test_rejects_health_or_malformed_events(self):
        for event in [{'id': 'x'}, self.event('x', path='/api/health'),
                      {**self.event('x'), 'latency_ms': float('nan')}]:
            with self.assertRaises(ValueError):
                self.store.record(event)

    def test_external_metric_has_real_quantity_and_discovery(self):
        self.store.record(self.event('a'))
        with patch.object(metrics, 'store', self.store):
            client = metrics.external.test_client()
            result = client.get('/apis/external.metrics.k8s.io/v1beta1/namespaces/default/api_requests_per_minute')
            self.assertEqual(result.json['items'][0]['value'], '1')
            self.assertEqual(result.json['items'][0]['windowSeconds'], 60)
            self.assertEqual(client.get('/apis/external.metrics.k8s.io/v1beta1').json['resources'][0]['verbs'], ['get'])
            self.assertEqual(client.get('/apis/external.metrics.k8s.io/v1beta1/namespaces/other/api_requests_per_minute').status_code, 404)

    def test_dashboard_uses_actual_deployment_pods_and_hpa(self):
        self.store.record(self.event('a', pod='api-1'))
        objects = (
            {'spec': {'replicas': 3}, 'status': {'replicas': 2, 'readyReplicas': 1}},
            {'items': [{'metadata': {'name': 'api-1', 'creationTimestamp': '2026-10-05T00:00:00Z'},
                        'status': {'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'True'}]}},
                       {'metadata': {'name': 'api-2'}, 'status': {'phase': 'Pending'}}]},
            {'status': {'currentReplicas': 2, 'desiredReplicas': 3,
                        'conditions': [{'type': 'ScalingActive', 'status': 'True'}]}})
        with patch.object(metrics, 'store', self.store), patch.object(metrics.reader, 'objects', return_value=objects):
            result = metrics.internal.test_client().get('/internal/dashboard')
        self.assertEqual(result.json['desired_replicas'], 3)
        self.assertEqual(result.json['current_replicas'], 2)
        self.assertEqual(result.json['ready_replicas'], 1)
        self.assertEqual(result.json['current_average_requests_per_minute'], 0.5)
        self.assertEqual(result.json['target_requests_per_minute'], 50)
        self.assertEqual(result.json['pods'][0]['requests_last_minute'], 1)
        self.assertTrue(result.json['pods'][0]['ready'])
        self.assertFalse(result.json['pods'][1]['ready'])
        self.assertEqual(result.json['autoscaler']['conditions'][0]['type'], 'ScalingActive')

    def test_dashboard_reads_changed_hpa_target_instead_of_default(self):
        for i in range(220):
            self.store.record(self.event(str(i)))
        hpa = {'spec': {'minReplicas': 1, 'maxReplicas': 5,
                        'metrics': [{'type': 'External', 'external': {
                            'metric': {'name': 'api_requests_per_minute'},
                            'target': {'type': 'AverageValue', 'averageValue': '75'}}}]},
               'status': {'currentReplicas': 5, 'desiredReplicas': 3}}
        objects = (
            {'spec': {'replicas': 5}, 'status': {'replicas': 5, 'readyReplicas': 5}},
            {'items': [{'metadata': {'name': 'api-' + str(i)},
                        'status': {'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'True'}]}}
                       for i in range(1, 6)]}, hpa)
        with patch.object(metrics, 'store', self.store), patch.object(metrics.reader, 'objects', return_value=objects):
            result = metrics.internal.test_client().get('/internal/dashboard')
        self.assertEqual(result.json['requests_last_minute'], 220)
        self.assertEqual(result.json['current_replicas'], 5)
        self.assertEqual(result.json['current_average_requests_per_minute'], 44)
        self.assertEqual(result.json['target_requests_per_minute'], 75)
        self.assertEqual(result.json['autoscaler']['target_requests_per_minute'], 75)
        self.assertEqual(result.json['recommended_replicas'], 3)
        self.assertEqual(result.json['autoscaler']['min_replicas'], 1)
        self.assertEqual(result.json['autoscaler']['max_replicas'], 5)

        # HPA의 범위를 바꾸어도 대시보드가 고정된 기본 범위를 표시하지 않습니다.
        hpa['spec'].update(minReplicas=2, maxReplicas=2)
        with patch.object(metrics, 'store', self.store), patch.object(metrics.reader, 'objects', return_value=objects):
            constrained = metrics.internal.test_client().get('/internal/dashboard').json
        self.assertEqual(constrained['recommended_replicas'], 2)
        self.assertEqual(constrained['autoscaler']['min_replicas'], 2)
        self.assertEqual(constrained['autoscaler']['max_replicas'], 2)


if __name__ == '__main__':
    unittest.main()
