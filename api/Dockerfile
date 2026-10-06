FROM python:3.12-slim
WORKDIR /app
ARG APP_VERSION=v1
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APP_VERSION=$APP_VERSION
COPY requirements.txt .
RUN pip install flask --trusted-host pypi.org --trusted-host files.pythonhosted.org
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
