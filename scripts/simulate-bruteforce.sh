#!/usr/bin/env bash
# Simula tentativas inválidas apenas contra a instância local TaskFlow.
set -euo pipefail

URL="http://127.0.0.1:8080"
ATTEMPTS="${1:-12}"

if [[ ! "$ATTEMPTS" =~ ^[0-9]{1,3}$ ]] || (( ATTEMPTS < 1 || ATTEMPTS > 100 )); then
  echo "Uso: $0 [número_de_tentativas_de_1_a_100]" >&2
  exit 2
fi

for ((attempt = 1; attempt <= ATTEMPTS; attempt++)); do
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --request POST "$URL/login" \
    --header 'Content-Type: application/json' \
    --data "{\"username\":\"admin\",\"password\":\"simulacao-invalida-${attempt}\"}")"
  if [[ "$status" != "401" ]]; then
    echo "Tentativa $attempt retornou HTTP $status; esperado 401." >&2
    exit 1
  fi
done

printf '%s tentativas inválidas concluídas contra %s/login (HTTP 401).\n' "$ATTEMPTS" "$URL"
echo "Consulte o Loki com a query de detecção em docs/runbook-login-bruteforce.md."
