# Roteiro da apresentação (~10 min). Mostrar repositório, PRs e Actions, não slides

1. **(1 min) Contexto**: nome do grupo, membros, quem fez o quê.
2. **(4 min) Demo ao vivo**: `./scripts/demo-shift-left.sh sqli` → aba Pull requests →
   checks rodando → `semgrep` vermelho → merge bloqueado → apagar `busca_legada.py`,
   push → tudo verde → merge. (Se sobrar tempo, repetir com `token` e o `gitleaks`.)
3. **(2 min) Antes × depois**: `git show baseline:app.py` (SQLi, SECRET_KEY, senha em texto
   puro) × `app.py` atual; `docs/hardening.md` com Trivy e `docker history`.
4. **(2 min) Decisão técnica**: (a) allowlist do Gitleaks restrita ao commit-baseline em vez de
   desligar a regra; (b) `ignore-unfixed` no Trivy e por que; (c) pin de actions por SHA.
5. **(1 min) Aprendizado mais impactante.**

Antes de apresentar: rodar o fluxo inteiro uma vez, com o relógio.
