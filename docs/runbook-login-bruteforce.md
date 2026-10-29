# Runbook: força bruta no login

| Campo | Procedimento |
|---|---|
| Severidade | Alta se houver login bem-sucedido associado; média para tentativas sem sucesso |
| Condição de disparo | Mais de 10 eventos `login_failure` do mesmo IP em cinco minutos |
| Responsável de plantão | Definir pelo grupo antes de usar em produção |

## Query de detecção

No Grafana, abra **Explore → Loki** e execute:

```logql
sum by (ip) (count_over_time({service="app"} | json | event="login_failure" [5m])) > 10
```

Registre o IP retornado, o intervalo consultado e a contagem. Os IPs observados a
partir do host podem ser endereços de gateway Docker.

## 1. Preparação

- Manter TaskFlow, coleta de logs JSON, Loki e Grafana disponíveis; a aplicação
  associa cada requisição a `request_id` e IP.
- Guardar `SECRET_KEY`, `ADMIN_PASSWORD` e `GRAFANA_ADMIN_PASSWORD` somente no `.env`
  local, com acesso restrito.
- Definir responsável e caminho de escalonamento; validar acesso administrativo ao
  host e ao firewall/security group.
- Executar periodicamente `./scripts/simulate-bruteforce.sh` em ambiente de teste.

## 2. Detecção e análise

1. Executar a query de detecção e registrar IP, contagem e janela temporal.
2. Identificar usuários mais visados:

   ```logql
   topk(5, sum by (username) (count_over_time({service="app"} | json | event="login_failure" [15m])))
   ```

3. Verificar se houve login bem-sucedido do IP no intervalo:

   ```logql
   {service="app"} | json | ip="<IP_OBSERVADO>" | event="login_success"
   ```

4. Correlacionar `request_id` com `request_completed` e confirmar status 401/200.
   Não coletar nem registrar senhas, cookies, tokens ou conteúdo de formulário.
5. Classificar como tentativa bloqueada ou possível comprometimento; preservar
   horário e resultados das consultas.

## 3. Contenção, erradicação e recuperação

- **Contenção:** bloquear o IP identificado no firewall/security group, considerando
  que pode ser um gateway compartilhado no laboratório. Se houver sucesso suspeito,
  revogar sessões alterando `SECRET_KEY` e reiniciando a aplicação.
- **Erradicação:** trocar a senha da conta visada e revisar alterações realizadas
  na conta no período.
- **Recuperação:** restaurar dados se necessário, confirmar o acesso legítimo e
  acompanhar a mesma query por 24 horas.

## 4. Atividade pós-incidente

- Registrar linha do tempo, tempo de detecção, contenção, impacto e evidências sem
  incluir credenciais ou cookies.
- Identificar melhorias necessárias, como rate limit e alertas automatizados.
- Atualizar este runbook e registrar lições aprendidas após o incidente.
