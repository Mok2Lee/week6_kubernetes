import os
import socket
import hashlib
import json
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from flask import Flask, g, jsonify, request
app = Flask(__name__)
app.json.ensure_ascii = False
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024
METRICS_URL = os.environ.get('METRICS_URL', '').rstrip('/')
POD_NAME = os.environ.get('POD_NAME') or socket.gethostname()
PENDING_EVENTS = deque()
PENDING_LOCK = threading.Lock()


def send_record(event):
    """Collector failure must not make the actual API fail; IDs prevent duplicates."""
    payload = json.dumps(event).encode('utf-8')
    req = Request(METRICS_URL + '/internal/record', data=payload,
                  headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(req, timeout=1.0) as response:
        if response.status != 200:
            raise RuntimeError('요청 통계 수집기가 응답하지 않습니다.')


def record_event(event):
    if not METRICS_URL:
        return 'disabled'
    try:
        send_record(event)
        return 'recorded'
    except (OSError, RuntimeError):
        # 실습용 메모리 대기열: 수집기가 복구되면 같은 ID로 다시 전달합니다.
        with PENDING_LOCK:
            PENDING_EVENTS.append(event)
        app.logger.warning('통계 전달 대기: request_id=%s', event['id'])
        return 'queued'


def retry_pending():
    while True:
        with PENDING_LOCK:
            event = PENDING_EVENTS[0] if PENDING_EVENTS else None
        if event:
            try:
                send_record(event)
                with PENDING_LOCK:
                    if PENDING_EVENTS and PENDING_EVENTS[0]['id'] == event['id']:
                        PENDING_EVENTS.popleft()
            except (OSError, RuntimeError):
                time.sleep(2)
        else:
            time.sleep(0.5)


@app.before_request
def begin_request():
    g.started = time.perf_counter()
    g.request_id = uuid.uuid4().hex


@app.after_request
def count_completed_request(response):
    # 준비 상태 검사, 대시보드 갱신, 실패한 요청은 부하 지표에 포함하지 않습니다.
    if request.path in {'/api/request', '/api/projects', '/api/analyze'} and 200 <= response.status_code < 300:
        elapsed = round((time.perf_counter() - g.started) * 1000, 2)
        event = {'id': g.request_id, 'pod': POD_NAME, 'path': request.path,
                 'latency_ms': elapsed, 'completed_at': datetime.now(timezone.utc).isoformat()}
        status = record_event(event)
        response.headers['X-Pod-Name'] = POD_NAME
        response.headers['X-Response-Time-Ms'] = str(elapsed)
        response.headers['X-Metrics-Status'] = status
        response.headers['X-App-Version'] = os.environ.get('APP_VERSION', 'v1')
        data = response.get_json(silent=True) if request.path == '/api/request' else None
        if isinstance(data, dict):
            data.update(pod=POD_NAME, version=os.environ.get('APP_VERSION', 'v1'),
                        latency_ms=elapsed, request_id=g.request_id, metrics_status=status)
            response.set_data(app.json.dumps(data))
    return response

@app.get('/api/health')
def health():
    with PENDING_LOCK:
        pending = len(PENDING_EVENTS)
    return jsonify(status='ok', version=os.environ.get('APP_VERSION', 'v1'),
                   pod=POD_NAME, metrics_pending=pending)


@app.get('/api/dashboard')
def dashboard():
    if not METRICS_URL:
        return jsonify(error='Kubernetes 통계 수집기가 연결되지 않았습니다.'), 503
    try:
        with urlopen(METRICS_URL + '/internal/dashboard', timeout=3) as response:
            data = json.load(response)
        return jsonify(data)
    except (OSError, ValueError):
        return jsonify(error='통계 수집기 또는 Kubernetes 상태를 확인할 수 없습니다.'), 503

@app.errorhandler(413)
def too_large(error):
    return jsonify(error='입력 내용이 너무 큽니다.'), 413


# 수정 실습: 예시 프로젝트를 추가하고 이미지를 다시 빌드하세요.
PROJECTS = [
    {'title':'교내 공간 예약', 'category':'web', 'description':'강의실과 스터디룸 예약 현황을 확인합니다.'},
    {'title':'캡스톤 팀원 모집', 'category':'web', 'description':'관심 분야와 기술에 맞는 팀원을 찾습니다.'},
    {'title':'실내 공기질 모니터', 'category':'iot', 'description':'센서로 교실의 온도와 공기질을 확인합니다.'},
    {'title':'분리배출 안내', 'category':'ai', 'description':'생활 폐기물의 분리배출 방법을 안내합니다.'},
]


@app.route('/api/request', methods=['GET', 'POST'])
def process_request():
    data = request.get_json(silent=True) if request.method == 'POST' else request.args
    data = data if isinstance(data, dict) or hasattr(data, 'get') else {}
    query = str(data.get('query', '')).strip()[:100]
    matches = [p['title'] for p in PROJECTS
               if query.casefold() in (p['title'] + ' ' + p['description']).casefold()]
    # 실제 작업: 프로젝트 검색 결과의 지문을 계산합니다. 대기 시간을 꾸미지 않습니다.
    digest = '|'.join(matches).encode('utf-8')
    for _ in range(2000):
        digest = hashlib.sha256(digest).digest()
    return jsonify(status='ok', result={'query': query, 'count': len(matches),
                                      'projects': matches, 'fingerprint': digest.hex()[:16]})

@app.get('/api/projects')
def projects():
    category = request.args.get('category', 'all')
    query = request.args.get('q', '').strip().casefold()
    rows = [p for p in PROJECTS
            if (category == 'all' or p['category'] == category)
            and query in (p['title'] + ' ' + p['description']).casefold()]
    return jsonify(items=rows, count=len(rows))

@app.post('/api/analyze')
def analyze():
    data = request.get_json(silent=True)
    text = data.get('text') if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        return jsonify(error='소개글을 입력하세요.'), 400
    if len(text) > 5000:
        return jsonify(error='소개글은 5,000자 이내로 입력하세요.'), 400
    # 공백과 줄바꿈도 글자 수에 포함합니다. 품질을 평가하는 기능은 아닙니다.
    return jsonify(characters=len(text), words=len(text.split()),
                   minimum=100, maximum=300, within_range=100 <= len(text) <= 300)

if __name__ == '__main__':
    if METRICS_URL:
        threading.Thread(target=retry_pending, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
