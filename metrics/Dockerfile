FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt .
RUN pip install flask --trusted-host pypi.org --trusted-host files.pythonhosted.org
RUN pip install cryptography --trusted-host pypi.org --trusted-host files.pythonhosted.org
COPY app.py generate_certs.py ./
EXPOSE 8000 8443
CMD ["python", "app.py"]
