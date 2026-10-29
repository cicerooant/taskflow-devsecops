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

O ZAP Baseline é um scanner passivo, portanto não executa as regras ativas 40012 e
40014. A regra passiva `10031` observa entrada controlada pelo usuário em atributos
HTML e permanece em `WARN`; regras não listadas são `INFO` por `-i`, e o workflow não
usa `-I`, então o aviso 10031 reprova o job.
Os achados de XSS persistente e erro de login também são cobertos por testes, pois
exigem autenticação/estado que o Baseline não configura. Os demais avisos listados em
`.zap/rules.tsv` são ignorados individualmente, com justificativa; não há
`continue-on-error` nem supressão global de avisos.

## Achados antes × depois

| Área | Antes (falha simulada) | Depois | OWASP Top 10:2021 |
|---|---|---|---|
| Busca `q` | Valor da URL refletido sem escape pode injetar HTML/script; validar se a regra passiva 10031 sinaliza o payload no relatório. | Jinja2 autoescapa `term`; testes verificam que o payload só aparece codificado. | A03: Injection |
| Título de tarefa | Título persistido e renderizado sem escape pode executar ao abrir a lista. | Jinja2 autoescapa `task.title`; teste automatizado cobre o payload armazenado. | A03: Injection |
| Erro de login | Username controlado pelo cliente poderia ser refletido sem escape. | O template renderiza a mensagem com autoescape; teste automatizado cobre esse sink. | A03: Injection |
| Diagnóstico | Endpoint `/debug/info` poderia expor configuração interna. | Endpoint removido; debug fica desligado por padrão e só é controlado por `FLASK_DEBUG`. | A05: Security Misconfiguration |

Para evidência da execução, baixe o artefato do job DAST no PR e registre o resultado
real do ZAP na apresentação. Os testes em `test_app.py` cobrem os sinks protegidos que
o scan passivo não percorre após autenticação.