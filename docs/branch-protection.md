# Proteção da branch `main`

Configure a proteção em **Settings → Branches → Branch protection rules** (ou
Rulesets) para `main`.

## Configuração obrigatória

- Exigir pull request antes do merge.
- Exigir que todos os checks abaixo passem antes do merge.
- Exigir branch atualizada antes do merge, se esse requisito estiver habilitado
  para o projeto.
- Bloquear force-push e exclusão da branch.

Selecione os nove status checks exatamente como aparecem no GitHub:

| Workflow | Status check |
|---|---|
| `ci.yml` | `lint-and-test` |
| `sast.yml` | `semgrep` |
| `sast.yml` | `gitleaks` |
| `sca.yml` | `pip-audit` |
| `container.yml` | `build-and-scan` |
| `dast.yml` | `zap-baseline` |
| `iac-scan.yml` | `checkov` |
| `iac-scan.yml` | `trivy-config` |
| `iac-scan.yml` | `terraform-validate` |

O workflow de IaC não deve ter filtro `paths:`. Como os três jobs são required
checks, um PR sem arquivos Terraform/Dockerfile ainda precisa executar os jobs e
reportar status; caso contrário, um check que não iniciou pode permanecer
pendente e bloquear o merge. Os workflows também permitem execução manual por
`workflow_dispatch`; `sca.yml` adicionalmente agenda uma execução semanal.

## Conferência via GitHub CLI

Depois de habilitar a proteção, confira a configuração atual:

```bash
gh api repos/cicerooant/taskflow-devsecops/branches/main/protection/required_status_checks
```

Para configurar os contexts de checks via API (preserve outros campos já
existentes na regra):

```bash
gh api \
  --method PATCH \
  repos/cicerooant/taskflow-devsecops/branches/main/protection/required_status_checks \
  -f strict=true \
  -f 'contexts[]=lint-and-test' \
  -f 'contexts[]=semgrep' \
  -f 'contexts[]=gitleaks' \
  -f 'contexts[]=pip-audit' \
  -f 'contexts[]=build-and-scan' \
  -f 'contexts[]=zap-baseline' \
  -f 'contexts[]=checkov' \
  -f 'contexts[]=trivy-config' \
  -f 'contexts[]=terraform-validate'
```

Os nomes dos jobs podem aparecer como status checks após pelo menos uma execução
do workflow. Confirme a grafia na lista de checks do GitHub antes de salvar a
regra de proteção.
