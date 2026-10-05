"""Integration checks against the real nginx -> Flask HTTP route."""
import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.parse import urlencode

base = 'http://localhost:8080'
def get(path):
    with urlopen(base + path, timeout=10) as response:
        assert response.status == 200
        return json.load(response)

with urlopen(base, timeout=10) as response:
    assert 'WEEK 6' in response.read().decode()
deadline = time.monotonic() + 20
matches = 0
while matches < 5:
    health = get('/api/health')
    matches = matches + 1 if health['version'] == sys.argv[1] else 0
    if matches < 5:
        assert time.monotonic() < deadline, health
        time.sleep(0.5)
assert health['status'] == 'ok'
assert health['version'] == sys.argv[1], health
assert health['pod'].startswith('api-'), health
assert get('/api/projects?' + urlencode({'q': '캡스톤'}))['count'] == 1
req = Request(base + '/api/analyze', data=json.dumps({'text': '가'*100}).encode(), headers={'Content-Type':'application/json'})
with urlopen(req, timeout=10) as response:
    assert json.load(response)['within_range'] is True
dashboard = get('/api/dashboard')
assert dashboard['window_seconds'] == 60, dashboard
assert dashboard['target_requests_per_minute'] in (50, 75), dashboard
assert dashboard['ready_replicas'] >= 1, dashboard
assert sum(endpoint['requests_last_minute'] for endpoint in dashboard['endpoints']) == dashboard['requests_last_minute']
assert sum(pod['requests_last_minute'] for pod in dashboard['pods']) == dashboard['requests_last_minute']
print('HTTP integration passed:', health)
