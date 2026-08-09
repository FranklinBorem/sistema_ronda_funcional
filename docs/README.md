# Especificação Técnica do Produto — Vigilante IA / Sistema Ronda

Este diretório é a **FASE -1 — Engenharia e Modelagem do Produto**. É documentação, não código. Nada aqui altera o comportamento do sistema; é a base de decisão para as fases seguintes (0 a 5).

## Como usar este material

Cada documento segue, quando há uma decisão relevante, o formato: **Problema → Alternativas → Vantagens → Desvantagens → Recomendação → Justificativa**. A recomendação é um ponto de partida para discussão, não uma decisão fechada — as decisões que exigem sua aprovação explícita estão centralizadas em `decisions/decisoes-pendentes.md`.

## Índice

| Documento | Conteúdo |
|---|---|
| [`product/visao-produto.md`](product/visao-produto.md) | Problema, público-alvo, personas, proposta de valor, produto atual vs. desejado vs. futuro |
| [`requirements/requisitos.md`](requirements/requisitos.md) | Requisitos funcionais e não funcionais, priorizados (MoSCoW) |
| [`architecture/casos-de-uso.md`](architecture/casos-de-uso.md) | Atores, casos de uso, diagrama Mermaid |
| [`architecture/modelo-dominio.md`](architecture/modelo-dominio.md) | Entidades de negócio — conceitual, antes de virar tabela |
| [`architecture/diagrama-classes.md`](architecture/diagrama-classes.md) | Diagrama de classes conceitual (Mermaid) — domínio vs. ORM vs. físico |
| [`database/modelo-banco.md`](database/modelo-banco.md) | Modelo lógico PostgreSQL, diagrama ER (Mermaid), decisões de índice/cardinalidade |
| [`database/multi-tenancy.md`](database/multi-tenancy.md) | Comparação de 5 estratégias de isolamento multi-cliente |
| [`architecture/arquitetura-aplicacao.md`](architecture/arquitetura-aplicacao.md) | Camadas, comparação de estilos arquiteturais, diagrama de componentes |
| [`architecture/fluxos-principais.md`](architecture/fluxos-principais.md) | 6 fluxos com diagramas de sequência (Mermaid) |
| [`architecture/equipamentos.md`](architecture/equipamentos.md) | Abstração de NVR/câmera, Adapter/Strategy/Factory, ONVIF |
| [`architecture/ia.md`](architecture/ia.md) | Pipeline de IA, acoplamento atual, arquitetura de regras/eventos |
| [`architecture/stack.md`](architecture/stack.md) | Avaliação tecnologia por tecnologia |
| [`architecture/frontend.md`](architecture/frontend.md) | Jinja vs. SPA — análise de custo/benefício |
| [`security/seguranca.md`](security/seguranca.md) | Modelo conceitual de segurança, MVP vs. futuro |
| [`architecture/deployment.md`](architecture/deployment.md) | Opções de deploy, diagrama, o problema dos NVRs atrás de firewall |
| [`architecture/estrutura-diretorios.md`](architecture/estrutura-diretorios.md) | Estrutura de pastas proposta, com justificativa |
| [`operations/testes.md`](operations/testes.md) | Estratégia de testes, exemplos conceituais |
| [`operations/ci-cd.md`](operations/ci-cd.md) | Git flow, PRs, lint, GitHub Actions |
| [`operations/observabilidade.md`](operations/observabilidade.md) | Monitoramento de produto vs. infraestrutura |
| [`decisions/roadmap-engenharia.md`](decisions/roadmap-engenharia.md) | Roadmap FASE -1 a FASE 5, com o que você vai aprender em cada uma |
| [`learning/plano-aprendizado.md`](learning/plano-aprendizado.md) | O que estudar antes/durante/depois de cada fase, como validar o aprendizado |
| [`decisions/documentacao.md`](decisions/documentacao.md) | Estrutura de `docs/`, uso de ADRs |
| [`decisions/decisoes-pendentes.md`](decisions/decisoes-pendentes.md) | **Lista de decisões que aguardam sua aprovação explícita** |

## Ordem de leitura recomendada

1. `product/visao-produto.md` — para alinhar "o quê" e "para quem" antes de qualquer técnica.
2. `requirements/requisitos.md` e `architecture/casos-de-uso.md` — o que o sistema precisa fazer.
3. `architecture/modelo-dominio.md` → `architecture/diagrama-classes.md` → `database/modelo-banco.md` — do conceito à tabela, nessa ordem (é assim que modelagem profissional funciona: nunca começar pela tabela).
4. `database/multi-tenancy.md` e `architecture/arquitetura-aplicacao.md` — as duas decisões estruturais mais caras de reverter depois.
5. Os documentos restantes podem ser lidos por interesse — não há dependência forte entre eles.
6. `decisions/decisoes-pendentes.md` por último — é o "resumo executivo do que você precisa decidir" depois de ler o resto.
