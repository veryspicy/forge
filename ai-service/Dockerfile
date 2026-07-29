FROM docker.io/library/python:3.12-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# Copy source (bind mount overlay for hot-reload)
COPY src/ src/

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
