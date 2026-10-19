# Hardening da imagem TaskFlow

Evidências geradas por `scripts/trivy-antes-depois.sh` (ficam em `docs/evidencias/`).

## Trivy (HIGH,CRITICAL): antes × depois
Gerado com Trivy 0.69.3 ("antes" em 18/10/2026; "depois" refeito em 19/10/2026, após o
Dependabot atualizar a base para 3.12.15 no PR #4). Saída completa em `docs/evidencias/trivy-*.txt`.

| | Antes (`taskflow:antes`) | Depois (`taskflow:depois`) |
|---|---|---|
| Imagem base | `python:3.9` (Debian 13, completa) | `python:3.12.15-slim-bookworm` (Debian 12.15) |
| CRITICAL (todas) | 235 | 2 |
| HIGH (todas) | 2.114 (2.108 SO + 6 Python) | 61 |
| **Total HIGH+CRITICAL** | **2.349** | **63** (−97%) |
| Com correção disponível (o que o gate avalia) | 2.014 | **0** |
| Tamanho da imagem (`docker image inspect`) | 410 MB | 50 MB |
| Usuário | root | appuser (10001) |
| Resultado no gate do CI | reprovaria | aprovado |

As 63 restantes são todas **sem correção** no Debian (55 `affected`, 7 `fix_deferred`,
1 `will_not_fix`). Por isso o gate usa `ignore-unfixed: true`; ver "Riscos aceitos".

## docker history: antes × depois
Ver `docs/evidencias/history-antes.txt` e `history-depois.txt`.
No "antes", o `ARG SECRET_KEY` e os `ENV SECRET_KEY` / `ENV ADMIN_PASSWORD` aparecem em
texto puro nos metadados das camadas: qualquer pessoa com acesso à imagem lê os segredos
com `docker history`, mesmo sem rodar o container. Nas evidências commitadas os valores
foram mascarados (`***REDACTED***`), porque commitá-los de novo seria reexpor o segredo
(e o Gitleaks bloquearia o PR).
No "depois", nenhuma camada contém segredo: `SECRET_KEY` e `ADMIN_PASSWORD` só entram em
runtime (`-e` / secret do orquestrador).

## As 6 falhas e a correção
| # | Falha no Dockerfile original | Correção |
|---|---|---|
| 1 | Base `python:3.9` sem versão de patch fixada | `python:3.12.15-slim-bookworm` (tag fixada) |
| 2 | Imagem base completa (toolchain, centenas de pacotes) | variante `slim` |
| 3 | Container roda como root | `USER appuser` (uid 10001) |
| 4 | Segredos em `ARG`/`ENV` | nenhum segredo na imagem; `SECRET_KEY` e `ADMIN_PASSWORD` só em runtime |
| 5 | Servidor de desenvolvimento (`python app.py`) | gunicorn |
| 6 | `FLASK_DEBUG=1` / `debug=True` e `COPY . .` sem `.dockerignore` | debug removido; `COPY app.py` + `.dockerignore` |

## Flags de runtime
Ver `docker-run-seguro.sh`: `--read-only`, `--cap-drop ALL`, `no-new-privileges`,
limites de memória/CPU/PIDs, porta publicada só em 127.0.0.1.

## Riscos aceitos
**Decisão do grupo:** o gate do Trivy reprova qualquer HIGH/CRITICAL **com correção
disponível** e usa `ignore-unfixed: true` para as que não têm correção no Debian, porque
nenhuma ação nossa (além de trocar de distro) as resolve, e um gate que nunca fica verde
vira gate ignorado. Para não depender só dessa flag:

- `apt-get upgrade` no build aplica todas as correções de segurança já publicadas para a
  base (troca consciente: build menos reprodutível em troca de patches imediatos);
- o Dependabot propõe toda semana novos patches da `python:3.12-slim-bookworm`;
- o `.trivyignore` está **vazio**: nenhuma CVE com correção foi aceita. Uma versão anterior
  listava 13 CVEs (Perl e OpenSSL); depois do `apt-get upgrade` verificamos que nenhuma era
  mais necessária e removemos todas, para a lista não esconder CVEs futuras.

CVEs sem correção que permanecem (63), por pacote:

| Pacote(s) | Qtde | Exposição na TaskFlow |
|---|---|---|
| util-linux e libs (`libblkid1`, `libmount1`, `mount`...) | 48 | Utilitários de sistema; a app não os invoca e o container roda sem capabilities (`--cap-drop ALL`) |
| `libsqlite3-0` (inclui CRITICAL CVE-2025-7458) | 3 | **Usada** pelo módulo `sqlite3`. Mitigação: só consultas parametrizadas, sem SQL vindo do usuário. Principal candidata a reavaliação quando houver fix |
| `zlib1g` (CRITICAL CVE-2023-45853, `will_not_fix`) | 1 | Falha no `minizip`, que a app não usa |
| ncurses, systemd/udev, gzip, acl, openssl/libssl3, perl-base | 11 | Sem uso direto pela app; aguardam fix do Debian |

Revisão: a cada PR do Dependabot na imagem base e na execução semanal do SCA.
