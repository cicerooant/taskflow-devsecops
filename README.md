# TaskFlow DevSecOps — Lab de Esteira Segura

![CI](../../actions/workflows/ci.yml/badge.svg)
![SAST](../../actions/workflows/sast.yml/badge.svg)
![SCA](../../actions/workflows/sca.yml/badge.svg)
![Container](../../actions/workflows/container.yml/badge.svg)

Grupo: _nome_ · Membros: _@user1 · @user2 · @user3_

## O que a esteira bloqueia
| Workflow | Job (check obrigatório) | Bloqueia quando |
|---|---|---|
| `ci.yml` | `lint-and-test` | ruff ou pytest falham |
| `sast.yml` | `semgrep` | Semgrep (`p/python`, `p/flask`, `p/security-audit`) acha qualquer problema |
| `sast.yml` | `gitleaks` | segredo em qualquer commit fora do baseline allowlistado |
| `sca.yml` | `pip-audit` | dependência com CVE conhecida |
| `container.yml` | `build-and-scan` | Trivy acha HIGH/CRITICAL corrigível, ou a imagem não sobe |

A `main` é protegida: PR obrigatório, CODEOWNERS e os 5 checks acima (ver `docs/branch-protection.md`).

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
- `docs/branch-protection.md`: configuração da `main`
- `docs/demo-roteiro.md`: roteiro da apresentação

## Histórico
O primeiro commit (tag `baseline`) é a TaskFlow **original e vulnerável**, mantida de propósito
para a comparação antes × depois. Os segredos dele são didáticos e estão allowlistados por SHA em `.gitleaks.toml`.
