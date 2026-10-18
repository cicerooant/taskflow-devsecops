#!/usr/bin/env bash
# Gera as evidências do docs/hardening.md: Trivy e docker history, antes x depois.
# Requer: docker, trivy e a tag git "baseline" (criada pelo criar-repo.sh).
set -euo pipefail
out=docs/evidencias
mkdir -p "$out"

rm -rf /tmp/tf-baseline && mkdir /tmp/tf-baseline
git archive baseline | tar -x -C /tmp/tf-baseline
docker build -q -t taskflow:antes /tmp/tf-baseline
docker build -q -t taskflow:depois .

for tag in antes depois; do
  trivy image --severity HIGH,CRITICAL --no-progress "taskflow:$tag" | tee "$out/trivy-$tag.txt" | tail -n 8
  docker history --no-trunc "taskflow:$tag" > "$out/history-$tag.txt"
  docker image inspect "taskflow:$tag" --format '{{.Config.User}}|{{.Size}}' > "$out/inspect-$tag.txt"
done
echo "Evidências em $out/. Copie os números para docs/hardening.md."
