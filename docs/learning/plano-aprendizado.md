# Plano de Aprendizado — Vigilante IA como Laboratório de Engenharia

Estrutura por fase: **o que aprender antes**, **o que estudar durante**, **o que praticar no código**, **como validar que aprendeu**.

---

## FASE -1 — Engenharia e Modelagem

**Aprender antes**: o que é modelagem de domínio (entidade, relacionamento, cardinalidade) e por que ela vem antes da tabela de banco; o que é UML de forma leve (caso de uso, classes, sequência, ER) — o suficiente para ler os diagramas Mermaid deste `docs/`, não um curso completo de UML.

**Estudar durante**: os próprios documentos produzidos nesta fase (`architecture/modelo-dominio.md`, `architecture/diagrama-classes.md`) — leia como se fosse um material de estudo, não só uma decisão para aprovar.

**Praticar**: nada de código ainda — praticar é **reescrever com suas palavras** um dos documentos (ex.: `database/multi-tenancy.md`) sem olhar o original, e comparar depois.

**Validar aprendizado**: você consegue explicar para outra pessoa, sem consultar o documento, por que a opção B (banco compartilhado + `empresa_id`) foi escolhida em vez de schema-por-cliente — incluindo o trade-off, não só a conclusão.

---

## FASE 0 — Segurança e Estabilização

**Aprender antes**: os fundamentos de segurança envolvidos (o que é um segredo hardcoded, por que hash de senha é diferente de criptografia reversível, o que é CSRF e por que ele explora sessão+cookie).

**Estudar durante**: leia o próprio bug do `subprocess.Popen` (`ronda_service.py`) como estudo de caso de "debugging por rastreamento de referência" — é um exemplo real de como um refactor incompleto quebra um fluxo sem nenhum erro óbvio no log.

**Praticar**:
- Corrigir a chamada quebrada (`RondaService`), testando manualmente antes/depois.
- Rodar `pg_dump`/restauração pelo menos uma vez, mesmo que "nada tenha dado errado" — o objetivo é ter feito o processo, não só saber que ele existe.
- Escrever a migration Alembic baseline para `nvr_monitorado`.

**Validar aprendizado**:
- Você consegue explicar por que `subprocess.Popen` falhou silenciosamente (sem lançar exceção visível) em vez de travar o processo inteiro — isso ensina sobre como processos filhos se comportam em Python.
- Você consegue restaurar o `pg_dump` sozinho, sem consultar nenhum guia.

---

## FASE 1 — Fundação do Produto

**Aprender antes**: chaves primárias e estrangeiras (PK/FK), JOIN, índices, o que é uma migration de dado (não só de schema) — migrar o campo texto `site` para uma tabela `unidades` é exatamente esse tipo de operação.

**Estudar durante**: o Adapter Pattern (`architecture/equipamentos.md`) como estudo de caso de "programar contra uma interface, não uma implementação" — um dos conceitos mais reaproveitáveis de toda a carreira de desenvolvimento.

**Praticar**:
- Criar a migration que adiciona `unidades` e migra o dado existente de `site` (texto) para a FK — inclui escrever a query de migração de dado, não só o `CREATE TABLE`.
- Extrair `HikvisionIsapiDriver` a partir do código já existente em `services/isapi_poller.py`, sem mudar o comportamento.
- Escrever os primeiros testes de integração.

**Validar aprendizado**:
- Você consegue explicar por que uma FK fica na tabela `nvrs` apontando para `unidades`, e não o contrário.
- Você identifica, olhando o código antigo, exatamente quais três arquivos tinham lógica ISAPI duplicada antes da extração do driver.
- Você escreve, sem ajuda, uma query SQL que lista todas as unidades de uma empresa com a contagem de NVRs de cada uma (JOIN + GROUP BY).

---

## FASE 2 — MVP Comercial (Multi-tenant)

**Aprender antes**: o que é isolamento de dado multi-tenant, o que é Row-Level Security do PostgreSQL, o que é autorização (diferente de autenticação) e como um decorator Python intercepta uma chamada de rota.

**Estudar durante**: o próprio documento `database/multi-tenancy.md` como estudo de caso de decisão arquitetural comparativa — é o modelo de como avaliar qualquer decisão técnica futura (não só multi-tenant): listar alternativas reais, comparar em critérios objetivos, recomendar com justificativa ligada ao contexto específico, não a uma regra geral.

**Praticar**:
- Adicionar `empresa_id` a uma tabela e escrever o filtro no repository correspondente.
- Escrever uma `CREATE POLICY` de Row-Level Security simples e testar que ela realmente bloqueia acesso cruzado.
- Escrever o teste automatizado de "duas empresas, dados isolados".

**Validar aprendizado**:
- Você consegue, dado um cenário fictício de duas empresas cadastradas, prever e depois confirmar que uma tentativa manual (via `curl`/console) de acessar dado de outra empresa é bloqueada — nas duas camadas (aplicação e RLS), separadamente, para entender o que cada uma faz.
- Você explica a diferença entre "autenticado" e "autorizado" usando um exemplo do próprio sistema (ex.: um Operador autenticado tentando acessar uma rota de Admin).

---

## FASE 3 — Primeiro Cliente

**Aprender antes**: o que muda quando existe um usuário real dependendo do sistema (diferente de ambiente de teste) — expectativa de disponibilidade, comunicação de incidente, priorização de bug.

**Estudar durante**: acompanhe métricas reais de uso pela primeira vez — é diferente de ler sobre métricas.

**Praticar**: escrever um manual básico de uso para o cliente; lidar com o primeiro bug relatado por alguém que não é você.

**Validar aprendizado**: você consegue triar um bug relatado por um usuário real (reproduzir, isolar causa, decidir prioridade) em um tempo razoável, sem pânico.

---

## FASE 4 — Escala

**Aprender antes**: índices compostos, `EXPLAIN ANALYZE` do PostgreSQL, particionamento de tabela, políticas de retenção de dado.

**Estudar durante**: rode `EXPLAIN ANALYZE` nas queries mais pesadas do sistema (ex.: dashboard) e compare antes/depois de um índice novo.

**Praticar**: implementar retenção/expurgo de `eventos_ia`/`auditoria` com base em volume real observado, não hipotético.

**Validar aprendizado**: você identifica, olhando um `EXPLAIN ANALYZE`, se uma query está usando um índice ou fazendo *sequential scan* — e sabe o que fazer a respeito.

---

## FASE 5 — IA Avançada e Integrações

**Aprender antes**: fundamentos de avaliação de modelo de visão computacional (precisão, recall, threshold de confiança) — necessário para avaliar se um segundo tipo de detecção está funcionando bem o suficiente para produção, não só "parece funcionar".

**Praticar**: adicionar o segundo tipo de detecção via `RegraDeteccao`, sem tocar em `core/ronda_multi_nvr.py` — é o teste prático de que a arquitetura da Fase 1 realmente funcionou.

**Validar aprendizado**: você consegue explicar, para uma detecção que "não pegou" um evento esperado, se o problema foi de modelo (recall baixo), de threshold (parâmetro da regra) ou de captura (imagem ruim) — diagnóstico em camadas, não um "deu errado" genérico.
