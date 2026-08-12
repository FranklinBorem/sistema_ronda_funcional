# Decisões que precisam da sua aprovação explícita

Nenhuma destas decisões deve ser implementada sem você confirmar — são as escolhas mais caras de reverter em todo este material.

---

### 1. Unificar `Nvr` e `NvrMonitorado` em uma única tabela? — **RESOLVIDA (contexto mudou)**
- **Status**: o banco de produção foi apagado (ação do TI) antes desta decisão ser implementada — não há mais dado legado a migrar/proteger, então o risco original desta decisão deixou de existir.
- **Decisão adotada**: unificar em uma única tabela `nvrs`, já refletida em `database/modelo-banco.md`, incluindo o ajuste adicional de `modo_conexao` em `cameras` (via NVR físico ou IP direto) definido em conversa posterior a este documento.
- Mantido aqui só como registro histórico — vira ADR formal (`ADR-001`) quando a primeira migration for aplicada, conforme `decisions/documentacao.md`.

### 2. Nível de rigor do isolamento multi-tenant desde o início
- **Opções**: (a) filtro de aplicação (`empresa_id` nos repositories) apenas; (b) filtro de aplicação + Row-Level Security desde a Fase 2; (c) RLS em todas as tabelas desde o início.
- **Minha recomendação**: (b) — RLS nas tabelas mais sensíveis (credenciais, ocorrências) desde já, expandindo depois.
- **Impacto**: RLS adiciona complexidade de configuração e depuração (queries que "não retornam nada" podem ser RLS bloqueando, não bug de lógica) — precisa ser uma escolha consciente, não descoberta durante debugging.
- **Por que precisa da sua decisão**: é a decisão de maior peso em segurança de todo o roadmap — vale você entender o trade-off antes de aceitar.

### 3. Modelo de deployment (Fase 2-3)
- **Opções**: (a) manter o modelo atual (servidor único + Cloudflare Tunnel) por mais tempo; (b) migrar para VPS/Cloud com túnel por cliente; (c) investir desde já no modelo de agente local (Fase 4 antecipada).
- **Minha recomendação**: (b) para o MVP, (c) só na Fase 4.
- **Impacto**: (b) exige migrar a operação atual do Grupo Ronda para um novo ambiente — não é sem risco, mesmo sendo recomendado.
- **Por que precisa da sua decisão**: envolve custo real (hospedagem) e uma janela de manutenção da operação atual.

### 4. Unificação de `Alerta` + `MonitorEvent` em `Ocorrencia` — tudo de uma vez ou em etapas?
- **Opções**: (a) migração completa de dado para a nova tabela `ocorrencias`; (b) `Ocorrencia` nasce como uma camada/view que agrega as duas tabelas existentes, sem migrar o dado histórico.
- **Minha recomendação**: (b) para reduzir risco na Fase 1, migrando de fato só se/quando fizer sentido.
- **Impacto**: (b) é mais rápido e seguro, mas mantém duas fontes de dado por baixo por mais tempo — dívida técnica consciente, não ausência de decisão.
- **Por que precisa da sua decisão**: troca velocidade por dívida técnica temporária; é uma escolha de prioridade, não só técnica.

### 5. Rigor de auditoria no MVP
- **Opções**: (a) auditoria mínima (ações de escrita administrativa); (b) auditoria completa desde o início (toda ação, inclusive leitura).
- **Minha recomendação**: (a).
- **Impacto**: (b) tem custo de armazenamento/performance maior sem benefício claro para o primeiro cliente.
- **Por que precisa da sua decisão**: se algum cliente-alvo específico já exige auditoria completa por contrato/compliance, isso muda a prioridade — informação que só você tem sobre o mercado que está mirando.

### 6. Migração de frontend (quando reconsiderar)
- **Opções**: já decidido evoluir gradualmente (Jinja2 + interatividade pontual) — mas fica em aberto **qual gatilho concreto** justificaria reconsiderar React no futuro.
- **Minha recomendação**: reconsiderar por tela específica (ex.: um editor de regras de detecção complexo), não como decisão geral do projeto.
- **Por que precisa da sua decisão**: você é quem vai sentir o atrito (ou não) de manter Jinja2 conforme o produto cresce — vale revisitar quando isso acontecer, não antecipar agora.

### 7. Ordem de execução: seguir a Fase 0 do plano de correção já produzido, ou revisar antes à luz desta especificação?
- **Minha recomendação**: seguir a Fase 0 como já está (ela já foi reclassificada considerando a visão de produto, na resposta anterior a este documento) — nenhum item da Fase 0 conflita com o que foi modelado aqui.
- **Por que precisa da sua decisão**: é o próximo passo prático — vale uma confirmação explícita antes de qualquer arquivo ser tocado.

---

Quando você aprovar (ou ajustar) cada uma dessas decisões, o passo seguinte natural é transformar a Fase 0 do roadmap em execução real, arquivo a arquivo, no mesmo formato já usado no plano de correção técnico.
