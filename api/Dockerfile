FROM python:3.12-slim
WORKDIR /app
ARG APP_VERSION=v1
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APP_VERSION=$APP_VERSION
COPY requirements.txt .
# 기본 경로: 서버 인증서를 검증하고 고정된 Flask 버전을 설치합니다.
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
