# Corrige as 6 falhas do Dockerfile original:
#  1. base com tag fixada      -> python:3.12.x-slim-bookworm (sem :latest)
#  2. base mínima              -> slim, sem toolchain de build
#  3. root                     -> USER não-root (uid 10001)
#  4. segredo em ENV/ARG       -> nenhum; SECRET_KEY/ADMIN_PASSWORD só em runtime
#  5. servidor de dev          -> gunicorn
#  6. debug ligado + COPY .    -> debug removido; .dockerignore limita o contexto
FROM python:3.12.12-slim-bookworm

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DB_PATH=/data/taskflow.db

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

RUN useradd --system --no-create-home --uid 10001 appuser \
 && mkdir /data && chown appuser:appuser /data
USER appuser
VOLUME /data

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--worker-tmp-dir", "/dev/shm", "--no-control-socket", "app:app"]
