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
autenticação que este scan não configura. O único rebaixamento mantido em
`.zap/rules.tsv` é a regra `10016`, pois `X-XSS-Protection` é um cabeçalho legado;
CSP e autoescape são os controles atuais. Os alertas de anti-framing, nosniff e CSRF
não são ignorados.

## Achados antes × depois — execução local

Os scans abaixo foram executados localmente em 29/10/2026 contra a aplicação na porta
`127.0.0.1:5000`, usando a mesma versão da imagem ZAP e os mesmos parâmetros do
Baseline (`-m 1`, threshold default informativo e spider limitado) e do active scan
(`.zap/xss-plan.yaml`). O alvo “antes” foi construído do commit anterior ao hardening;
o “depois” usou o código atual. Os totais são instâncias de alertas dos relatórios
JSON/HTML, não contagens estimadas:

| Scan | High antes → depois | Medium antes → depois | Low antes → depois | Informational antes → depois |
|---|---:|---:|---:|---:|
| ZAP Baseline | 0 → 0 | 10 → 0 | 13 → 6 | 8 → 9 |
| Plano ativo focado em XSS (`40012`) | 0 → 0 | 12 → 0 | 3 → 0 | 2 → 4 |

O Baseline anterior registrou 3 tipos Medium (CSRF `10202` ×3, CSP `10038` ×5,
anti-clickjacking `10020` ×2) e 2 ocorrências de `X-Content-Type-Options` ausente
(`10021`, Low). A execução posterior reportou **zero Medium ou High**; os 6 Low
restantes são os achados de isolamento cross-origin `90004`. O único IGNORE mantido é
`10016`, ausente da contagem anterior e posterior.

No plano ativo, o `exitStatus` configurado para High foi aprovado antes e depois; os
alertas Medium do relatório anterior eram observações passivas do spider, não alertas
de XSS. Depois, o relatório não contém alertas Medium ou High e a regra XSS refletido
continua habilitada e foi exercitada pelo plano.

| Área | Antes | Depois | OWASP Top 10:2021 |
|---|---|---|---|
| CSP, clickjacking e nosniff | CSP ausente: `10038` Medium ×5; framing: `10020` Medium ×2; nosniff: `10021` Low ×2. | CSP restritiva sem `unsafe-inline`, `X-Frame-Options: DENY` e `X-Content-Type-Options: nosniff`; esses alertas não aparecem. | A05: Security Misconfiguration |
| CSRF | Ausência de token: `10202` Medium ×3; formulários POST não eram protegidos. | Token aleatório por sessão em todos os formulários POST; POST form sem token retorna 403; JSON continua isento. | A01: Broken Access Control |
| Cache e permissões | Cache e Permissions Policy ausentes foram observados. | `Cache-Control: no-store` e `Permissions-Policy` restritiva; sem alerta correspondente. | A05: Security Misconfiguration |
| Busca `q` / XSS refletido | O plano ativo foi aprovado; alerta passivo `10031` aparece como Informational. | Autoescape mantido; plano ativo aprovado novamente e `10031` continua Informational, sem Medium/High. | A03: Injection |
| Título de tarefa e erro de login | Testes existentes cobriam escaping destes valores. | Testes permanecem; Jinja2 autoescapa os valores. | A03: Injection |
| Diagnóstico | `/debug/info` não existe nesta versão; a resposta é 404. | Continua inexistente; debug fica desligado por padrão e controlado por `FLASK_DEBUG`. | A05: Security Misconfiguration |