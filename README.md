# TaskFlow DevSecOps — Lab de Esteira Segura

![CI](../../actions/workflows/ci.yml/badge.svg)
![SAST](../../actions/workflows/sast.yml/badge.svg)
![SCA](../../actions/workflows/sca.yml/badge.svg)
![Container](../../actions/workflows/container.yml/badge.svg)
![DAST](../../actions/workflows/dast.yml/badge.svg)

Grupo: _nome_ · Membros: _@user1 · @user2 · @user3_

## O que a esteira bloqueia
| Workflow | Job (check obrigatório) | Bloqueia quando |
|---|---|---|
| `ci.yml` | `lint-and-test` | ruff ou pytest falham |
| `sast.yml` | `semgrep` | Semgrep (`p/python`, `p/flask`, `p/security-audit`) acha qualquer problema |
| `sast.yml` | `gitleaks` | segredo em qualquer commit fora do baseline allowlistado |
| `sca.yml` | `pip-audit` | dependência com CVE conhecida |
| `container.yml` | `build-and-scan` | Trivy acha HIGH/CRITICAL corrigível, ou a imagem não sobe |
| `dast.yml` | `zap-baseline` | ZAP encontra XSS bloqueante ou a app não sobe |

A `main` é protegida: PR obrigatório, CODEOWNERS e os 6 checks acima (ver `docs/branch-protection.md`).

## Arquitetura e workflows
TaskFlow é uma aplicação Flask com API JSON, páginas Jinja2 e banco SQLite. No workflow
DAST, a imagem da aplicação sobe no runner do GitHub Actions e o ZAP Baseline verifica a
busca HTML antes de a imagem ser encerrada. O relatório fica disponível como artefato do job.

`ci.yml`, `sast.yml`, `sca.yml`, `container.yml` e `dast.yml` rodam em pull requests,
pushes para `main` e por `workflow_dispatch`; `sca.yml` também roda semanalmente. Para
reexecutar manualmente, use Actions → workflow → Run workflow. O check `zap-baseline` deve
ser marcado como obrigatório na proteção da `main` após sua primeira execução.

## Rodando localmente
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && pytest -q
export SECRET_KEY=$(openssl rand -hex 32) ADMIN_PASSWORD='troque-esta-senha' COOKIE_SECURE=0
python app.py
```

## Docs
- `docs/hardening.md`: Trivy e docker history, antes × depois
- `docs/dast.md`: DAST com ZAP, achados e mapeamento OWASP Top 10
- `docs/branch-protection.md`: configuração da `main`
- `docs/demo-roteiro.md`: roteiro da apresentação

## Histórico
O primeiro commit (tag `baseline`) é a TaskFlow **original e vulnerável**, mantida de propósito
para a comparação antes × depois. Os segredos dele são didáticos e estão allowlistados por SHA em `.gitleaks.toml`.
