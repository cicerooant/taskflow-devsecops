# DAST com OWASP ZAP Baseline

O workflow `.github/workflows/dast.yml` constrói a imagem, sobe a TaskFlow no runner,
aguarda `/login` responder e roda o ZAP Baseline em `/tasks?q=...` com um payload
de prova que tenta injetar um atributo de evento; sem sessão, essa busca mostra
somente o formulário de login e não expõe tarefas. O relatório HTML é publicado como
artefato `zap-baseline-report`, inclusive quando o job falha.
O arquivo é gravado em um diretório temporário separado do checkout para evitar
problemas de permissão entre o usuário do runner e o usuário do container ZAP.
As regras são montadas em `/zap/wrk`, caminho exigido pelo `zap-baseline.py` para
opções que leem arquivos.

O ZAP Baseline é passivo; por isso, o workflow também executa
`.zap/xss-plan.yaml`, um active scan restrito à regra `40012` (XSS refletido), em
força baixa, com duração máxima de um minuto e um thread por host. O `exitStatus`
reprova o job para alertas High. Isso permite provar o gate sem executar o Full Scan
genérico, que é mais amplo e caro. O relatório do active scan e o do Baseline são
publicados juntos como artefato.

A regra passiva `10031` continua documentada na configuração Baseline. XSS
persistente e erro de login permanecem cobertos por testes, pois exigem estado ou
autenticação que este scan não configura. Os avisos aceitos em `.zap/rules.tsv` têm
justificativas individuais; não há `continue-on-error` nem supressão global de alertas.

## Achados antes × depois

| Área | Antes (falha simulada) | Depois | OWASP Top 10:2021 |
|---|---|---|---|
| Busca `q` | Valor refletido sem escape é detectado pelo active scan 40012 como XSS refletido High. | Jinja2 autoescapa `term`; o mesmo plano focado termina sem alerta High. | A03: Injection |
| Título de tarefa | Título persistido e renderizado sem escape pode executar ao abrir a lista. | Jinja2 autoescapa `task.title`; teste automatizado cobre o payload armazenado. | A03: Injection |
| Erro de login | Username controlado pelo cliente poderia ser refletido sem escape. | O template renderiza a mensagem com autoescape; teste automatizado cobre esse sink. | A03: Injection |
| Diagnóstico | Endpoint `/debug/info` poderia expor configuração interna. | Endpoint removido; debug fica desligado por padrão e só é controlado por `FLASK_DEBUG`. | A05: Security Misconfiguration |

Para evidência da execução, baixe o artefato do job DAST no PR e registre o resultado
real do ZAP na apresentação. Os testes em `test_app.py` cobrem os sinks protegidos que
o scan passivo não percorre após autenticação.