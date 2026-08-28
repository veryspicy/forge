FROM docker.io/library/python:3.12-slim

WORKDIR /app

# Use Aliyun mirror for faster apt (Debian bookworm)
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy source first (needed for editable install)
COPY pyproject.toml .
COPY casbin_model.conf .
COPY seed_admin.py .
COPY src/ src/

# Install Python dependencies in editable mode (bind mount friendly)
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir --default-timeout=600 -e "."

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "forge.main.application:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
