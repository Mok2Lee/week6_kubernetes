import os
import socket
from flask import Flask, jsonify, request
app = Flask(__name__)
app.json.ensure_ascii = False
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024

@app.get('/api/health')
def health():
    return jsonify(status='ok', version=os.environ.get('APP_VERSION', 'v1'), pod=socket.gethostname())

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
    app.run(host='0.0.0.0', port=5000, debug=False)
