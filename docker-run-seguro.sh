#!/usr/bin/env bash
# Executa a TaskFlow com flags de runtime seguras. Segredos vêm do ambiente do host.
set -euo pipefail
: "${SECRET_KEY:?defina SECRET_KEY (ex.: export SECRET_KEY=\$(openssl rand -hex 32))}"
: "${ADMIN_PASSWORD:?defina ADMIN_PASSWORD}"

docker run -d --name taskflow \
  --read-only --tmpfs /tmp \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 100 --memory 256m --cpus 0.5 \
  -e SECRET_KEY -e ADMIN_PASSWORD -e COOKIE_SECURE=0 \
  -v taskflow-data:/data \
  -p 127.0.0.1:5000:5000 \
  "${IMAGE:-taskflow:latest}"
