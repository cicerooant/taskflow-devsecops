# TaskFlow DevSecOps — Esteira Segura

![CI](../../actions/workflows/ci.yml/badge.svg)
![SAST](../../actions/workflows/sast.yml/badge.svg)
![SCA](../../actions/workflows/sca.yml/badge.svg)
![Container](../../actions/workflows/container.yml/badge.svg)
![DAST](../../actions/workflows/dast.yml/badge.svg)
![IaC](../../actions/workflows/iac-scan.yml/badge.svg)

Grupo: _nome_ · Membros: _@user1 · @user2 · @user3_

TaskFlow é uma aplicação Flask com API JSON, páginas Jinja2 e banco SQLite. Este
repositório reúne CI, SAST, SCA, análise de container, DAST, análise de IaC e
observabilidade local.

## Arquitetura

```text
 Navegador ──► 127.0.0.1:8080 ──► [TaskFlow: Flask + Gunicorn]
                                         │
                                         ├── SQLite em volume local persistente
                                         └── stdout: eventos JSON com request_id
                                                   │
                         Docker socket (read-only) └──► [Promtail] ──► [Loki]
                                                                         ▲
                                                     [Grafana :3000] ────┘
```

- O Compose publica somente a aplicação em `127.0.0.1:8080`. A rede `backend` é
  `internal: true`; não há serviço de banco de rede porque o app usa SQLite.
- A aplicação usa filesystem read-only, tmpfs, volume SQLite, healthcheck, limites
  de CPU/memória, `cap_drop: ALL` e `no-new-privileges`.
- Loki e Promtail comunicam-se na rede de observabilidade. Grafana e Loki só
  publicam suas portas no loopback. Grafana tem datasource Loki provisionado,
  cadastro desativado e acesso anônimo desativado.
- Promtail coleta apenas containers com label `logging=promtail`. O acesso de
  leitura ao socket Docker é um trade-off de segurança do laboratório.
- Logs JSON incluem IP e UUID da requisição; senhas, cookies, tokens e conteúdo
  de formulário não são registrados. Títulos e termos de busca entram somente
  como tamanhos.
- `infra/` contém recursos AWS Terraform: bucket de dados S3 privado, versionado
  e criptografado com KMS/rotação; bucket separado para access logs; security
  group com ingress `/32` validado e egress restrito.

## Workflows e checks obrigatórios

Todos os workflows rodam em pull requests, em push para `main` e via
`workflow_dispatch`, salvo o SCA que também roda semanalmente. Para executar
manualmente: GitHub → **Actions** → workflow correspondente → **Run workflow**.
Os nomes abaixo são os nomes de jobs a marcar como required status checks.

| Workflow | Check obrigatório | Gate |
|---|---|---|
| `ci.yml` | `lint-and-test` | Ruff e pytest |
| `sast.yml` | `semgrep` | Regras Python, Flask e security audit |
| `sast.yml` | `gitleaks` | Segredos fora do baseline allowlistado |
| `sca.yml` | `pip-audit` | Vulnerabilidades conhecidas em dependências |
| `container.yml` | `build-and-scan` | Build, Trivy HIGH/CRITICAL corrigível e smoke test |
| `dast.yml` | `zap-baseline` | ZAP Baseline e active scan limitado a XSS |
| `iac-scan.yml` | `checkov` | Checkov para Terraform e Dockerfile |
| `iac-scan.yml` | `trivy-config` | Trivy config HIGH/CRITICAL |
| `iac-scan.yml` | `terraform-validate` | `terraform fmt`, init sem backend e validate |

`iac-scan.yml` **não usa filtro `paths:`** porque seus três jobs são checks
obrigatórios. Se um filtro impedisse o workflow de iniciar em um PR sem mudanças
de IaC, o status check poderia ficar pendente e bloquear o merge. Os jobs rodam em
todo PR para que os checks obrigatórios sempre reportem resultado.

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

Crie `.env` local a partir do modelo e preencha os valores gerados localmente;
`.env` é ignorado pelo Git, enquanto `.env.example` contém apenas chaves vazias:

```bash
cp .env.example .env
printf 'SECRET_KEY=%s\nADMIN_PASSWORD=%s\nGRAFANA_ADMIN_PASSWORD=%s\n' \
  "$(openssl rand -hex 32)" \
  "$(openssl rand -hex 32)" \
  "$(openssl rand -hex 32)" > .env
```

Suba TaskFlow e a stack de observabilidade:

```bash
docker compose -f docker-compose.yml -f docker-compose.observabilidade.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.observabilidade.yml ps
```

TaskFlow: `http://127.0.0.1:8080`; Grafana: `http://127.0.0.1:3000`
(usuário `admin`, senha configurada em `GRAFANA_ADMIN_PASSWORD` no `.env`).
Consulte [docs/observabilidade.md](docs/observabilidade.md) e
[docs/runbook-login-bruteforce.md](docs/runbook-login-bruteforce.md) para as
consultas Loki e a simulação de tentativas de login.

Para validar IaC localmente:

```bash
docker compose config -q
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra init -backend=false
terraform -chdir=infra validate
checkov -d . --framework terraform,dockerfile --quiet --compact
trivy config --severity HIGH,CRITICAL --exit-code 1 .
```

## Documentação

- [docs/hardening.md](docs/hardening.md): hardening e análise de imagem Trivy
- [docs/dast.md](docs/dast.md): ZAP, resultados reais antes/depois e OWASP Top 10
- [docs/observabilidade.md](docs/observabilidade.md): Loki, Promtail, Grafana e LogQL
- [docs/runbook-login-bruteforce.md](docs/runbook-login-bruteforce.md): resposta a incidente
- [docs/branch-protection.md](docs/branch-protection.md): proteção da branch `main`
- [docs/demo-roteiro.md](docs/demo-roteiro.md): roteiro de demonstração

## Histórico

O primeiro commit (tag `baseline`) é a TaskFlow original vulnerável, mantida para
comparação. Os segredos didáticos desse histórico são allowlistados por SHA em
`.gitleaks.toml`.
