# syntax=docker/dockerfile:1.7

FROM python:3.12.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    SERVING_STATE_ROOT=/var/lib/kserve-platform

WORKDIR /opt/kserve-platform

RUN groupadd --gid 65532 runtime \
    && useradd --uid 65532 --gid 65532 --no-create-home --shell /usr/sbin/nologin runtime \
    && install -d -o 65532 -g 65532 /var/lib/kserve-platform

COPY pyproject.toml requirements-serving.lock README.md LICENSE ./
COPY src ./src

RUN python -m pip install --upgrade "pip==25.3" \
    && python -m pip install --constraint requirements-serving.lock ".[serving]" \
    && python -m pip check

USER 65532:65532

EXPOSE 8080
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=10s --timeout=2s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/v2/health/ready', timeout=1).read()"]

ENTRYPOINT ["uvicorn"]
CMD ["kserve_model_platform.api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log", "--proxy-headers", "--timeout-graceful-shutdown", "10"]
