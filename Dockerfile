FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    MODEL_ROOT=/app/artifacts/models \
    MODEL_VERSION=baseline-v1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 service \
    && useradd --uid 10001 --gid service --no-create-home service
COPY --chown=service:service ml_service ./ml_service
USER service
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"
CMD ["python", "-m", "uvicorn", "ml_service.inference.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
