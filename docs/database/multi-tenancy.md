# Multi-Tenancy — Comparação de Estratégias

## Problema

Comercializar o Vigilante IA para múltiplos clientes exige garantir que os dados de um cliente nunca sejam visíveis ou acessíveis por outro. Existem várias formas arquiteturais de resolver isso, com trade-offs bem diferentes de segurança, custo e complexidade operacional.

## Alternativas

### A. Uma instalação por cliente (deploy dedicado)
Cada cliente roda sua própria instância completa da aplicação e do banco (servidor/VPS/container dedicado por cliente).

| Critério | Avaliação |
|---|---|
| Segurança | Máxima — isolamento físico, impossível vazar dado entre clientes por bug de aplicação |
| Complexidade | Alta a médio prazo — N clientes = N ambientes para atualizar, monitorar, corrigir |
| Custo | Cresce linearmente com o número de clientes (infraestrutura dedicada por cliente) |
| Manutenção | Cada deploy de correção precisa ser replicado em todas as instâncias |
| Escalabilidade | Ruim para SaaS de muitos clientes pequenos; boa para poucos clientes grandes |
| Isolamento | Total |
| Backup | Simples por cliente, mas N vezes o trabalho operacional |
| Deploy | Repetitivo, propenso a divergência entre instâncias ao longo do tempo |
| Adequação | Boa para clientes enterprise com exigência contratual de isolamento físico; ruim como modelo padrão de SaaS |

### B. Banco compartilhado + `empresa_id` (row-level multi-tenancy)
Uma única aplicação, um único banco, toda tabela relevante carrega `empresa_id`, e todo acesso é filtrado por ele.

| Critério | Avaliação |
|---|---|
| Segurança | Depende de disciplina de aplicação — mitigável com Row-Level Security do PostgreSQL como segunda camada |
| Complexidade | Baixa — é a extensão mais natural do que já existe (banco único, models já centralizados em repositories) |
| Custo | Mínimo — um único ambiente para todos os clientes |
| Manutenção | Uma correção, um deploy, todos os clientes atualizados |
| Escalabilidade | Boa para dezenas/centenas de clientes de porte pequeno-médio |
| Isolamento | Lógico, não físico — depende de implementação correta |
| Backup | Um backup cobre todos os clientes (simples operacionalmente, mas restaurar para "só o cliente X" é mais trabalhoso) |
| Deploy | Simples — um único pipeline |
| Adequação | Adequada ao estágio atual (poucos clientes, equipe de um desenvolvedor) |

### C. Schema PostgreSQL por cliente
Um banco só, mas cada cliente tem seu próprio schema (`cliente_a.usuarios`, `cliente_b.usuarios`).

| Critério | Avaliação |
|---|---|
| Segurança | Boa — isolamento reforçado pelo próprio motor de banco, sem depender de `WHERE empresa_id = ...` em cada query |
| Complexidade | Média-alta — SQLAlchemy/Alembic não lidam nativamente bem com múltiplos schemas dinâmicos; cada novo cliente exige criar schema + rodar migrations nele |
| Custo | Baixo (um único servidor de banco) |
| Manutenção | Migration precisa rodar em N schemas — cresce em complexidade com o número de clientes |
| Escalabilidade | Boa até algumas dezenas de clientes; PostgreSQL começa a sofrer com milhares de schemas |
| Isolamento | Melhor que B, pior que A |
| Backup | Pode restaurar schema individual, mas ferramental é menos padronizado |
| Deploy | Complexidade adicional de rodar migration por schema a cada novo cliente/atualização |
| Adequação | Faz mais sentido quando há dezenas de clientes de porte médio e a equipe já tem maturidade operacional — prematuro agora |

### D. Banco separado por cliente
Cada cliente tem seu próprio banco de dados (mesmo servidor físico ou não).

| Critério | Avaliação |
|---|---|
| Segurança | Muito boa — praticamente equivalente à opção A em isolamento de dado |
| Complexidade | Alta — gestão de N conexões/credenciais de banco, migrations em N bancos |
| Custo | Médio a alto, dependendo de como os bancos são hospedados |
| Manutenção | Similar à opção C, com isolamento ainda maior, mas complexidade operacional maior também |
| Escalabilidade | Limitada pela capacidade de gerenciar múltiplas conexões/bancos manualmente |
| Isolamento | Muito alto |
| Backup | Simples por cliente, granular |
| Deploy | Migration precisa rodar em N bancos |
| Adequação | Faz sentido para clientes enterprise com exigência regulatória forte — não para o MVP |

### E. Arquitetura híbrida
Banco compartilhado (opção B) como padrão, com a opção de "promover" um cliente específico (ex.: enterprise, com exigência contratual) para banco dedicado (opção A/D) quando necessário.

| Critério | Avaliação |
|---|---|
| Segurança | Flexível — nível de isolamento por cliente conforme necessidade/contrato |
| Complexidade | Média — exige que a aplicação já esteja desenhada para não assumir "sempre o mesmo banco" (ex.: resolução de conexão por empresa) |
| Custo | Baixo para a maioria, alto só para os clientes que exigem isolamento físico |
| Manutenção | A base comum (B) recebe a maior parte do esforço; exceções são raras |
| Escalabilidade | Boa — cresce como B, com válvula de escape para casos especiais |
| Isolamento | Ajustável |
| Adequação | É o destino natural de longo prazo, mas **não precisa ser construído agora** — a opção B bem feita já permite migrar clientes específicos para isolamento físico depois, sem redesenho, se a aplicação já centraliza acesso a dado nos repositories |

## Recomendação

**Opção B (banco compartilhado + `empresa_id`) agora, com o caminho para híbrido (E) deixado aberto por boas práticas de código, não construído antecipadamente.**

## Justificativa para este projeto especificamente

1. **Estágio atual**: um desenvolvedor, poucos clientes esperados no início. As opções A/C/D introduzem complexidade operacional (gestão de múltiplos ambientes/schemas/bancos) que não se paga no volume esperado — você mesmo definiu como princípio "não quero arquitetura exagerada porque poderia crescer".
2. **O código já está no formato certo para B**: a camada de repositories (`repositories/*.py`) já centraliza o acesso a dado — inserir o filtro `empresa_id` sistematicamente é uma mudança concentrada, não espalhada por todo o código. Isso não seria verdade se o projeto tivesse SQL espalhado em rotas (não é o caso aqui).
3. **O risco de B (vazamento por bug de aplicação) é mitigável, não é motivo para descartar a opção**: Row-Level Security do PostgreSQL (`CREATE POLICY`) funciona nativamente com o banco já usado (PostgreSQL, confirmado em `config.py`), sem exigir troca de tecnologia — é a segunda camada de defesa que torna B tão segura quanto justificável para este estágio.
4. **B não fecha a porta para E**: se um cliente futuro exigir isolamento físico contratualmente, migrá-lo para um banco dedicado é possível justamente porque o acesso a dado já está centralizado — não seria uma reescrita, seria trocar a resolução da conexão de banco para aquele tenant específico.

**Importante — não é "multi-tenant é sempre a resposta certa só porque queremos vender"**: se o modelo de negócio mirasse desde já poucos clientes enterprise muito grandes com exigência contratual de isolamento físico (ex.: setor bancário/governo), a opção A ou D seria defensável desde o início. Não é o caso descrito na sua visão de produto (múltiplas empresas de porte variado, incluindo pequenas) — por isso B é a recomendação, não uma resposta automática.
