# Roadmap de Engenharia — Vigilante IA

Cada fase inclui, além do técnico, **o que você vai aprender** (conforme o objetivo declarado de usar este projeto como laboratório de engenharia de software). O plano de aprendizado detalhado está em `learning/plano-aprendizado.md` — aqui é o resumo por fase.

---

## FASE -1 — Engenharia e Modelagem
- **Objetivo**: ter uma especificação técnica clara antes de tocar em código (este próprio conjunto de documentos).
- **Conhecimentos**: levantamento de requisitos, modelagem de domínio, UML/diagramas, trade-off arquitetural documentado (Problema → Alternativas → Recomendação).
- **Funcionalidades**: nenhuma — só documentação.
- **Arquitetura**: definida (monólito modular, ver `architecture/arquitetura-aplicacao.md`).
- **Banco**: modelo lógico definido (`database/modelo-banco.md`), nenhuma migration aplicada.
- **Segurança**: modelo conceitual definido (`security/seguranca.md`).
- **Testes**: estratégia definida (`operations/testes.md`), nenhum teste escrito ainda.
- **Documentação**: este próprio `docs/`.
- **Critério de conclusão**: você consegue explicar, sem consultar este documento, por que a arquitetura escolhida é a adequada para o estágio atual (esse é o teste real de que a Fase -1 cumpriu seu papel de aprendizado, não só de planejamento).

## FASE 0 — Segurança e Estabilização
- **Objetivo**: corrigir os bugs/vulnerabilidades confirmados sem mexer em arquitetura — base estável para construir em cima (detalhado etapa a etapa no plano de correção já produzido).
- **Conhecimentos**: debugging de causa raiz (o caso do `subprocess.Popen` apontando para arquivo inexistente é um exemplo real de "seguir referências antes de corrigir"), segredo/configuração segura, backup e rollback de banco.
- **Funcionalidades**: nenhuma nova — ronda volta a funcionar, segredo removido, endpoints autenticados.
- **Arquitetura**: nenhuma mudança estrutural.
- **Banco**: baseline Alembic para `nvr_monitorado`.
- **Segurança**: itens críticos do plano de correção (categoria A).
- **Testes**: primeiros testes manuais guiados (checklist de cada etapa do plano de correção) — ainda sem automação.
- **Documentação**: nenhuma nova além do que já existe.
- **Critério de conclusão**: ronda dispara e conclui de ponta a ponta; nenhum segredo em texto no repositório; `flask db upgrade` funciona limpo em ambiente novo.

## FASE 1 — Fundação do Produto
- **Objetivo**: preparar a base de dados/código para multi-tenant, ainda com um único cliente.
- **Conhecimentos**: modelagem relacional na prática (migrar campo texto para FK, ver `database/modelo-banco.md`/`Unidade`), Adapter Pattern (extrair `NvrDriver`), primeiros testes automatizados.
- **Funcionalidades**: entidade `Unidade` real; início da unificação `Ocorrencia`.
- **Arquitetura**: extração do `NvrDriver` (`architecture/equipamentos.md`); estrutura de regra de detecção (`architecture/ia.md`), com comportamento idêntico ao atual.
- **Banco**: nova tabela `unidades`, migração de dado do campo texto; `regras_deteccao`/`eventos_ia` criadas (não usadas para novos tipos ainda).
- **Segurança**: CSRF, rate limiting no login.
- **Testes**: primeira suíte real (integração dos fluxos críticos, migrations).
- **Documentação**: ADRs das decisões tomadas nesta fase (ver `decisions/documentacao.md`).
- **Critério de conclusão**: sistema continua 100% funcional para o cliente atual, agora com `Unidade` como entidade e driver de equipamento isolado; suíte de testes cobre os fluxos críticos.

## FASE 2 — MVP Comercial (multi-tenant)
- **Objetivo**: sistema capaz de hospedar mais de uma empresa com isolamento real.
- **Conhecimentos**: multi-tenancy na prática, Row-Level Security do PostgreSQL, autorização por papel, testes de segurança dedicados.
- **Funcionalidades**: `Empresa`, `Usuario.papel`, `UsuarioUnidade`, onboarding administrado (não self-service).
- **Arquitetura**: filtro de tenant centralizado nos repositories; decorator de autorização por papel.
- **Banco**: `empresa_id` em todas as tabelas relevantes; RLS nas tabelas mais sensíveis.
- **Segurança**: auditoria básica; teste automatizado dedicado a vazamento entre tenants.
- **Testes**: cenário de duas empresas fictícias, validado automaticamente.
- **Documentação**: atualização do modelo de banco físico real (pós-migration).
- **Critério de conclusão**: duas empresas de teste operando na mesma instância sem nenhum vazamento de dado, validado por teste automatizado — não só manual.

## FASE 3 — Primeiro Cliente
- **Objetivo**: colocar um cliente real (o próprio Grupo Ronda migrado + um piloto) em produção.
- **Conhecimentos**: operar um sistema com usuário real (diferente de ambiente de teste), suporte/triagem de bug em produção, revisão de segurança para exposição externa.
- **Funcionalidades**: dashboard consolidado, notificações configuráveis por empresa.
- **Arquitetura**: estabilização, sem mudança estrutural nova.
- **Banco**: revisão de índices com dado real de mais de uma empresa.
- **Segurança**: revisão de exposição externa (o piloto acessa via internet).
- **Testes**: acompanhamento ativo, canal rápido de correção.
- **Documentação**: manual básico de uso para o cliente piloto.
- **Critério de conclusão**: cliente piloto operando autonomamente por um período definido (ex. 30 dias) sem intervenção manual no banco.

## FASE 4 — Escala
- **Objetivo**: suportar crescimento sem degradar nem exigir intervenção manual constante.
- **Conhecimentos**: performance de banco (índices, particionamento), políticas de retenção de dado, observabilidade mais madura.
- **Funcionalidades**: planos/limites por empresa; retenção de séries temporais.
- **Arquitetura**: avaliar fila de jobs para ronda/inferência, só se o volume real demonstrar necessidade.
- **Banco**: retenção definida com base em uso real; particionamento se necessário.
- **Segurança**: RLS expandida para todas as tabelas restantes.
- **Testes**: testes de carga básicos.
- **Documentação**: runbook de operação (o que fazer quando X acontece).
- **Critério de conclusão**: sistema suporta a carteira de clientes atual com folga observável de recursos.

## FASE 5 — IA Avançada e Integrações
- **Objetivo**: expandir diferencial competitivo, validando as abstrações construídas nas fases anteriores.
- **Conhecimentos**: avaliação e integração de novos modelos de IA, integração com segundo fabricante de equipamento, design de API pública.
- **Funcionalidades**: segundo tipo de detecção; segundo fabricante de NVR; possivelmente API pública.
- **Arquitetura**: nenhuma mudança estrutural nova — uso pleno do que já foi construído.
- **Critério de conclusão**: adicionar um novo tipo de detecção ou fabricante não exige alterar `core/ronda_multi_nvr.py` — prova de que a arquitetura das fases anteriores cumpriu o objetivo de extensibilidade sem reescrita.
