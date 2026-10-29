# Observabilidade: TaskFlow, Promtail, Loki e Grafana

## Preparar e subir a stack

O `.env` local precisa conter `SECRET_KEY`, `ADMIN_PASSWORD` e
`GRAFANA_ADMIN_PASSWORD`. Copie o modelo e gere cada valor localmente:

```bash
cp .env.example .env
openssl rand -hex 32
```

Armazene cada resultado apenas em `.env`; não o cole em comandos compartilhados nem
o versione. Suba os serviços:

```bash
docker compose -f docker-compose.yml -f docker-compose.observabilidade.yml up -d --build
```

TaskFlow fica em `http://127.0.0.1:8080`, Grafana em `http://127.0.0.1:3000`
(usuário `admin`, senha `GRAFANA_ADMIN_PASSWORD`) e a API Loki fica disponível
somente em `127.0.0.1:3100` para consultas e validações locais. Grafana não permite
cadastro e não habilita acesso anônimo.

Promtail descobre containers pelo socket Docker montado em modo somente leitura e
filtra exclusivamente o label `logging=promtail`; esse label é aplicado ao serviço
TaskFlow. O acesso ao socket continua sendo um privilégio relevante do host e é uma
limitação explícita do laboratório.

## Eventos e privacidade

Cada evento da aplicação é uma linha JSON no stdout com `request_id` (UUID),
`ip`, timestamp e nível. A resposta também devolve o UUID no header `X-Request-ID`.
Os eventos de negócio incluem `login_success`, `login_failure`, `task_created` e
`tasks_listed`; `request_completed` registra método, caminho, status e duração.

Login registra usuário e IP, nunca senha. Criação de tarefa registra apenas o
tamanho do título; listagem registra quantidade de resultados e tamanho da busca.
Não são logados texto de título/busca, cookie, token ou corpo/formulário.

## Consultas LogQL

No Grafana, abra **Explore → Loki**. Estas consultas foram testadas contra o Loki
local depois da simulação de 12 tentativas; os resultados medidos foram **12
falhas de login do mesmo IP**, 12 respostas HTTP 401 e um usuário visado:

1. Falhas de login por IP nos últimos cinco minutos (query do runbook):

   ```logql
   sum by (ip) (count_over_time({service="app"} | json | event="login_failure" [5m]))
   ```

   Resultado observado nesta execução: IP `172.21.0.1`, contagem `12`. Esse endereço
   é o gateway da rede Docker usado pelo host; pode variar em outra máquina.

2. Usuários mais visados nos últimos 15 minutos:

   ```logql
   topk(5, sum by (username) (count_over_time({service="app"} | json | event="login_failure" [15m])))
   ```

   Resultado observado: `admin`, contagem `12`.

3. Respostas 4xx/5xx por status nos últimos cinco minutos:

   ```logql
   sum by (status) (count_over_time({service="app"} | json | event="request_completed" | status >= 400 [5m]))
   ```

   Resultado observado: status `401`, contagem `12`.

4. Consultar todos os eventos de uma requisição usando o identificador recebido:

   ```logql
   {service="app"} | json | request_id="<X-Request-ID>"
   ```

O tráfego originado no host costuma chegar ao container com o IP de gateway da rede
Docker, não com o endereço público de quem opera o host. Use o IP retornado pela
consulta como IP atacante observado neste laboratório.

## Simulação

Com a stack ativa, execute `./scripts/simulate-bruteforce.sh` (por padrão, 12
tentativas). A senha usada na simulação é fictícia, não é exibida e não é registrada.
Consulte a primeira query acima; a contagem deve corresponder ao número de tentativas.

O Promtail é usado por exigência do exercício, embora esteja em manutenção upstream.
