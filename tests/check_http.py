"""Integration checks against the real nginx -> Flask HTTP route."""
import json
import sys
from urllib.request import Request, urlopen
from urllib.parse import urlencode

base = 'http://localhost:8080'
def get(path):
    with urlopen(base + path, timeout=10) as response:
        assert response.status == 200
        return json.load(response)

with urlopen(base, timeout=10) as response:
    assert 'WEEK 6' in response.read().decode()
health = get('/api/health')
assert health['status'] == 'ok'
assert health['version'] == sys.argv[1], health
assert health['pod'].startswith('api-'), health
assert get('/api/projects?' + urlencode({'q': '캡스톤'}))['count'] == 1
req = Request(base + '/api/analyze', data=json.dumps({'text': '가'*100}).encode(), headers={'Content-Type':'application/json'})
with urlopen(req, timeout=10) as response:
    assert json.load(response)['within_range'] is True
print('HTTP integration passed:', health)
