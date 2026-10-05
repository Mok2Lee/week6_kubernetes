FROM python:3.12-slim
WORKDIR /app
ARG APP_VERSION=v1
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APP_VERSION=$APP_VERSION
COPY requirements.txt .
# 학교 실습용: 아래 두 패키지 호스트의 인증서 검증만 생략합니다.
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
