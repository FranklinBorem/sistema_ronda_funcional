# Documentação do Projeto

## Estrutura proposta (a que este próprio material já segue)

```
docs/
├── product/        → visão de produto, personas, proposta de valor (o "porquê" de negócio)
├── requirements/     → requisitos funcionais/não funcionais priorizados
├── architecture/      → modelo de domínio, diagramas, decisões estruturais, fluxos
├── database/           → modelo lógico, ER, estratégia de multi-tenancy
├── api/                  → (ainda vazio — só passa a existir quando houver API pública real, Fase 5; não criar pasta especulativa antes disso)
├── operations/            → testes, CI/CD, observabilidade
├── security/                → modelo de segurança
├── decisions/                 → roadmap, ADRs, decisões pendentes de aprovação
└── learning/                    → plano de aprendizado
```

A estrutura que você propôs já fazia sentido — a única alteração é **não criar `docs/api/` fisicamente ainda**, para não deixar uma pasta vazia sem propósito no repositório; ela nasce junto com o primeiro conteúdo real (Fase 5).

## O que muda ao longo do tempo

- `product/` e `requirements/` são revisados quando a visão de produto muda (não a cada sprint).
- `architecture/` e `database/` são atualizados **quando uma decisão estrutural é tomada ou revista** — não precisam ser reescritos a cada funcionalidade pequena.
- `decisions/` recebe um ADR novo a cada decisão importante (ver abaixo) — cresce ao longo de todo o projeto, nunca é "reescrito", só acumulado.
- `learning/` é seu diário de estudo — atualize à medida que cada fase avança, registrando o que realmente foi aprendido (pode divergir do planejado, e isso é esperado e válido).

## Architecture Decision Records (ADRs)

**O que é**: um registro curto e imutável de uma decisão arquitetural — não um documento vivo que se reescreve, mas um "log" histórico. Uma vez escrito, um ADR não é editado quando a decisão muda; em vez disso, escreve-se um novo ADR que **supera** o anterior, referenciando-o.

**Formato sugerido** (leve, não burocrático):
```
# ADR 001 — [Título curto da decisão]

Data: AAAA-MM-DD
Status: proposto | aceito | superado por ADR-00X

## Contexto
Qual problema motivou esta decisão?

## Decisão
O que foi decidido.

## Alternativas consideradas
Lista breve, com o principal motivo de descarte de cada uma.

## Consequências
O que fica mais fácil, o que fica mais difícil, o que precisa ser observado depois.
```

**Como vamos usar neste projeto**: cada decisão marcada como "recomendação" nos documentos deste `docs/` (ex.: a escolha de banco compartilhado + `empresa_id` em `database/multi-tenancy.md`) vira um ADR formal em `decisions/adr/` **no momento em que for aprovada e implementada** — não antes. O ADR funciona como o "porquê" congelado no tempo, para que, daqui a um ano, ninguém (nem você) precise adivinhar por que aquela escolha foi feita, ou refazer a mesma discussão do zero.

**Numeração**: sequencial (`ADR-001`, `ADR-002`, ...), nunca reutilizada, mesmo que um ADR seja superado depois — a numeração é o histórico, não o estado atual.

**Quando escrever um ADR** (regra prática): sempre que uma decisão for cara de reverter (troca de banco, escolha de multi-tenancy, escolha de framework, mudança de modelo de dado central) — decisões pequenas e reversíveis (nome de uma variável, escolha de uma biblioteca de lint) não precisam de ADR.
