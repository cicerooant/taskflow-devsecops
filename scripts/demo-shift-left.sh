#!/usr/bin/env bash
# Cria um branch com uma falha de segurança e abre um PR, para demonstrar o shift-left.
#   ./scripts/demo-shift-left.sh sqli    -> query concatenada (Semgrep deve bloquear)
#   ./scripts/demo-shift-left.sh token   -> token de teste no código (Gitleaks deve bloquear)
# Requer: git e gh (autenticado).
set -euo pipefail
tipo="${1:?uso: $0 sqli|token}"
git switch main && git pull --ff-only
git switch -c "demo/${tipo}-$(date +%H%M%S)"

case "$tipo" in
  sqli)
    cat > busca_legada.py <<'PY'
import sqlite3


def buscar_usuario(db_path, nome):
    conn = sqlite3.connect(db_path)
    return conn.execute("SELECT * FROM users WHERE username = '" + nome + "'").fetchall()
PY
    git add busca_legada.py
    git commit -m "feat: busca de usuário (DEMO: query concatenada)"
    ;;
  token)
    # Token FALSO gerado na hora (formato de PAT do GitHub), nunca um token real.
    printf 'GITHUB_TOKEN = "ghp_%s"\n' "$(openssl rand -hex 18)" > config_demo.py
    git add config_demo.py
    git commit -m "feat: config de integração (DEMO: token no código)"
    ;;
  *) echo "tipo inválido"; exit 1 ;;
esac

git push -u origin HEAD
gh pr create --fill --base main
echo "Mostre os checks vermelhos e o merge bloqueado. Para corrigir: apague o arquivo, commit e push."
