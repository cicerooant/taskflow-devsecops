# Hardening da imagem TaskFlow

Evidências geradas por `scripts/trivy-antes-depois.sh` (ficam em `docs/evidencias/`).

## Trivy (HIGH,CRITICAL): antes × depois
| | Antes (`taskflow:antes`) | Depois (`taskflow:depois`) |
|---|---|---|
| CRITICAL | _preencher_ | _preencher_ |
| HIGH | _preencher_ | _preencher_ |
| Tamanho da imagem | _preencher_ | _preencher_ |
| Usuário | root | appuser (10001) |

## docker history: antes × depois
Ver `docs/evidencias/history-antes.txt` e `history-depois.txt`.
No "antes", o `ARG SECRET_KEY` e os `ENV` com segredo aparecem em texto puro nas camadas.
No "depois", não há segredo em nenhuma camada.

## As 6 falhas e a correção
| # | Falha no Dockerfile original | Correção |
|---|---|---|
| 1 | Base `python:3.9` sem versão de patch fixada | `python:3.12.12-slim-bookworm` (tag fixada) |
| 2 | Imagem base completa (toolchain, centenas de pacotes) | variante `slim` |
| 3 | Container roda como root | `USER appuser` (uid 10001) |
| 4 | Segredos em `ARG`/`ENV` | nenhum segredo na imagem; `SECRET_KEY` e `ADMIN_PASSWORD` só em runtime |
| 5 | Servidor de desenvolvimento (`python app.py`) | gunicorn |
| 6 | `FLASK_DEBUG=1` / `debug=True` e `COPY . .` sem `.dockerignore` | debug removido; `COPY app.py` + `.dockerignore` |

> Conferir esta lista com a das Aulas 3 do material da disciplina e ajustar a numeração.

## Flags de runtime
Ver `docker-run-seguro.sh`: `--read-only`, `--cap-drop ALL`, `no-new-privileges`,
limites de memória/CPU/PIDs, porta publicada só em 127.0.0.1.

## Riscos aceitos
O gate do Trivy usa `ignore-unfixed: true`: CVEs HIGH/CRITICAL **sem correção disponível**
na base Debian não derrubam o build, pois o grupo não tem como corrigi-las. Registrar aqui
cada CVE aceita (ID, pacote, motivo) quando houver.
