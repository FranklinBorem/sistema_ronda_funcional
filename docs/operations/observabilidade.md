# Observabilidade

## Distinção importante

- **Monitoramento do produto** (do software que você constrói): erros de aplicação, latência de rotas, saúde dos workers/threads internas, taxa de sucesso das rondas.
- **Monitoramento da infraestrutura** (do que o produto observa no mundo do cliente): disponibilidade de câmeras/NVRs — isso é, na verdade, uma **funcionalidade do produto** (módulo de Conferência), não "observabilidade do sistema" no sentido de DevOps. É fácil confundir os dois porque o produto literalmente monitora infraestrutura de terceiros como seu propósito de negócio — mas monitorar "a aplicação está de pé" é uma preocupação diferente de "os NVRs do cliente estão de pé".

## Erros

- **MVP**: `@app.errorhandler` global + `logger.exception()` em pontos que hoje engolem exceção silenciosamente (já mapeado no plano de correção) — grava em `logs/vigilante.log` (já existe o mecanismo de log, `RotatingFileHandler`, conforme `app.py`).
- **Futuro**: agregador de erros externo (ex.: Sentry) quando o volume de usuários justificar não depender só de grep em arquivo de log.

## Logs

- **MVP**: manter o `RotatingFileHandler` já configurado, garantindo que `*.log.1`/rotações não sejam commitadas no Git (correção já mapeada) e que os logs tenham contexto suficiente (usuário, empresa, ação) para investigação.
- **Futuro**: log estruturado (JSON) com `request_id`/`empresa_id` correlacionável, facilitando investigar um incidente de um cliente específico sem vasculhar log de todos.

## Saúde da aplicação

- **MVP**: um endpoint simples de health-check (`/health` retornando 200 se a aplicação e a conexão com o banco estão OK) — útil tanto para monitoramento manual quanto para, futuramente, um orquestrador de deploy verificar se o processo subiu corretamente.
- **Futuro**: métricas de latência/throughput por rota (ex.: via Prometheus), se a operação crescer a ponto de precisar de alerta automático de degradação.

## Saúde dos workers (threads de ronda/conferência)

- **MVP**: logging claro de início/fim de cada execução de ronda e de cada ciclo de polling — hoje já existe parcialmente; junto com a correção do bug de disparo de ronda (plano de correção), garantir que uma ronda "travada" (nunca sai de `em_andamento`) seja visível em log, não silenciosa.
- **Futuro**: um dashboard interno (ou aba do próprio produto) mostrando "última execução do poller de conferência: há X minutos" — detecta se o próprio motor do produto parou de funcionar, não só se um NVR do cliente caiu.

## Saúde dos NVRs / disponibilidade de câmeras

Isso já é o módulo de Conferência do produto (`services/isapi_poller.py`, `services/conferencia_loop.py`) — não é uma ferramenta de observabilidade separada, é a funcionalidade central de negócio sendo usada, inclusive, para você mesmo acompanhar a saúde da própria operação de desenvolvimento/testes.

## Desempenho

- **MVP**: acompanhamento manual — tempo de resposta do dashboard, tempo de execução de uma ronda completa.
- **Futuro**: métricas automatizadas quando o volume justificar (ligado a RNF08 em `requirements/requisitos.md`, adiado deliberadamente para a Fase 4).

## Resumo do mínimo necessário para o MVP

1. Erros de aplicação logados com contexto (não engolidos silenciosamente).
2. Um endpoint de health-check simples.
3. Log de início/fim de cada ronda e ciclo de polling, para detectar workers travados.
4. Rotação de log funcionando sem poluir o repositório Git (já mapeado no plano de correção).

Tudo além disso (Sentry, métricas Prometheus, dashboards de observabilidade dedicados) é Fase 4+, quando o custo de não ter essas ferramentas começar a doer de verdade — não antes.
