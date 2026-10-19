#!/usr/bin/env bash
# Cria um branch com uma falha de segurança e abre um PR, para demonstrar o shift-left.
#   ./scripts/demo-shift-left.sh sqli    -> query concatenada (Semgrep deve bloquear)
#   ./scripts/demo-shift-left.sh token   -> token de teste no código (Gitleaks deve bloquear)
# Requer: git (e gh autenticado para abrir o PR sozinho; sem gh, abra pelo link do push).
set -euo pipefail
tipo="${1:?uso: $0 sqli|token}"
git switch main && git pull --ff-only
git switch -c "demo/${tipo}-$(date +%H%M%S)"

case "$tipo" in
  sqli)
    # Troca a consulta parametrizada da busca de tarefas (GET /tasks?q=) por concatenação.
    # Precisa ser numa rota Flask: a regra tainted-sql-string do p/flask segue o dado de
    # request.args até a query. Um arquivo solto com SQL concatenado NÃO é detectado.
    # --cached aplica sobre o índice (LF), evitando falha por CRLF no Windows.
    git apply --cached <<'PATCH'
diff --git a/app.py b/app.py
index 99a7a2c..8330cec 100644
--- a/app.py
+++ b/app.py
@@ -114,8 +114,8 @@ def create_app(test_config=None):
         rows = (
             get_db()
             .execute(
-                "SELECT id, title, done FROM tasks WHERE owner_id = ? AND title LIKE ?",
-                (uid, f"%{term}%"),
+                "SELECT id, title, done FROM tasks WHERE owner_id = "
+                + str(uid) + " AND title LIKE '%" + term + "%'"
             )
             .fetchall()
         )
PATCH
    git checkout -- app.py
    git commit -m "feat: busca de tarefas (DEMO: query concatenada)"
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
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  gh pr create --fill --base main
else
  echo "gh não encontrado/autenticado: abra o PR pelo link que o GitHub mostrou acima."
fi

cat <<MSG

Mostre o check vermelho e o merge bloqueado. Para corrigir (e ver o verde):
  sqli:  git revert --no-edit HEAD && git push
  token: o Gitleaks varre todos os commits do PR, então revert NÃO resolve; reescreva:
         git reset --hard origin/main && git push --force-with-lease
         (com token real, além disso: revogar o token imediatamente)
MSG
