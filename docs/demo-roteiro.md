# Roteiro da Apresentação (~10 min) — Atividade 2
# Foco: DAST, IaC e Observabilidade. Mostrar o repositório, PRs e a stack rodando.

**Preparação prévia:** Deixar a stack (App + Loki + Grafana) rodando no terminal. Ter o PR de teste aberto e a aba do Grafana pronta em outra janela. Ter prints e um vídeo curto como Plano B.

## 1. (1 min) Contexto: O que mudou desde a Atividade 1
*   Apresentação do grupo e divisão de tarefas.
*   Evolução da esteira: saímos apenas da análise estática (SAST) e passamos a atacar a aplicação rodando no pipeline (DAST), validar a infraestrutura (IaC) e preparar o time para responder a incidentes (Observabilidade).

## 2. (4 min) Demo ao vivo: DAST e o bloqueio do merge
*   Mostrar o código do template `templates/tasks.html` e explicar a correção do XSS (Uso do Jinja2 com autoescape).
*   **Simular a falha:** Fazer um commit rápido revertendo a correção (adicionando `| safe` de volta) e abrir um PR.
*   **A esteira agindo:** Ir na aba "Actions" do PR. Mostrar o `dast.yml` subindo a app e o **ZAP Baseline** atacando. O check do ZAP fica **vermelho**.
*   **A trava:** Mostrar que o botão de "Merge" está bloqueado.
*   **A correção:** Desfazer a alteração (voltar o autoescape), dar push. Mostrar o ZAP passando (verde) e o merge liberado.

## 3. (2 min) IaC: Segurança na infraestrutura
*   Mostrar o arquivo `infra/main.tf` e `docker-compose.yml`.
*   Mostrar a aba "Actions" rodando o `iac-scan.yml`.
*   Explicar o gate do **Checkov** e do **Trivy Config**: se a infraestrutura estiver insegura, o pipeline barra o PR.
*   Mostrar rapidamente uma justificativa de skip no código (`#checkov:skip=...`) para provar que não desligamos os scanners, mas avaliamos os riscos.

## 4. (2 min) Incidente ao vivo: Ataque e Resposta (O momento mais importante!)
*   **Ação:** Rodar `./scripts/simulate-bruteforce.sh` no terminal (12 tentativas de login inválidas).
*   **Detecção:** Abrir o Grafana (Explore), rodar a query do runbook (`sum by (ip) (count_over_time(...) > 10)`) e mostrar o gráfico com os 12 erros e o IP atacante.
*   **O Runbook:** Abrir o `docs/runbook-login-bruteforce.md` e explicar rapidamente as 4 fases do NIST (Preparação, Detecção, Contenção/Erradicação, Pós-incidente) apontando como o log estruturado com `request_id` ajuda na investigação.

## 5. (1 min) Decisão técnica e trade-off
*   **Decisão:** Por que manter SQLite em vez de um banco em rede? (Simplicidade para o lab, o arquivo do banco fica em um volume seguro).
*   **Trade-off:** Por que o Promtail lê o socket do Docker? (Facilidade de coletar logs sem mudar a aplicação, mas exige dar privilégios ao container do Promtail).
*   **Aprendizado:** A importância de logs JSON sem dados sensíveis (sem senhas) para que o Loki não armazene dados críticos.

---
**Plano B:** Se a rede ou os containers falharem no dia, mostrar os vídeos curtos e os prints salvos em `docs/evidencias/`.