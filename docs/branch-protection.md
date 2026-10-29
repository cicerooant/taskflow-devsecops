# Branch protection da `main` (Aula 1)

> **Atenção:** em repositório **privado**, proteção de branch exige plano pago
> (GitHub Pro/Team). Contas Free não aplicam a regra. Alunos podem ativar o
> **GitHub Student Developer Pack** (Pro grátis) ou criar o repositório numa organização.

## Pela interface
Settings → Branches → Add branch ruleset (ou *Add classic branch protection rule*) para `main`:

- [x] Require a pull request before merging (1 aprovação)
- [x] Require review from Code Owners
- [x] Require status checks to pass before merging, marcando:
  `lint-and-test`, `semgrep`, `gitleaks`, `pip-audit`, `build-and-scan`, `zap-baseline`
  (os checks só aparecem na lista depois de rodarem uma vez)
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings (inclui administradores)

## Pelo `gh` CLI
```bash
gh api -X PUT repos/OWNER/REPO/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint-and-test", "semgrep", "gitleaks", "pip-audit", "build-and-scan", "zap-baseline"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null
}
JSON
```

## Como provar que o gate funciona
Abra um PR com `scripts/demo-shift-left.sh sqli`: o check `semgrep` fica vermelho e o
botão de merge fica bloqueado. Print/gravação disso é a evidência do critério de 25%.
