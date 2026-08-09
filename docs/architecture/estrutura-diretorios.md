# Estrutura de Diretórios — Proposta

## Estrutura atual (confirmada por leitura do repositório)

```
app.py, config.py, extensions.py     ← raiz da aplicação
core/                                 ← motor de deteccao, auth decorator, config de NVR
models/                               ← ORM
repositories/                         ← acesso a dado
services/                             ← regra de negocio
routes/                               ← blueprints Flask
templates/                            ← Jinja2
migrations/                           ← Alembic
server.js, package.json               ← bot WhatsApp (Node.js)
scripts soltos na raiz                ← utilitarios administrativos (seed, limpeza, debug)
```

## Problema

Essa estrutura já é razoável (é a base do "monólito modular" recomendado em `architecture/arquitetura-aplicacao.md`), mas tem duas fraquezas relevantes para o produto comercial: (1) scripts administrativos soltos na raiz misturados com o código de produção; (2) nenhum lugar natural para as novas peças (drivers de equipamento, regras de IA, documentação).

## Estrutura proposta (evolução, não substituição)

```
app.py, config.py, extensions.py

core/
  auth.py                  (mantém)
  ronda_multi_nvr.py        (mantém — motor de deteccao)
  ronda_loop.py              (mantém)

models/                     (mantém, cresce com novas entidades: empresa, unidade, ocorrencia...)
repositories/                (mantém, cresce)
services/                    (mantém, cresce)
routes/                       (mantém, cresce)
templates/                     (mantém)
migrations/                     (mantém, com disciplina — sem scripts ad-hoc de criação de tabela)

integrations/                    ← NOVO: drivers de equipamento (Adapter Pattern)
  nvr_driver.py                    (interface NvrDriver)
  hikvision_isapi_driver.py        (migrado de services/isapi_poller.py)
  driver_factory.py

ai/                                ← NOVO: regras de deteccao, catalogo de modelos
  regra_deteccao.py
  modelo_yolo.py                   (encapsula o que hoje esta hardcoded em core/ronda_multi_nvr.py)

scripts/                           ← NOVO: move os utilitarios administrativos da raiz
  seed.py, limpar_rondas.py, debug_isapi.py, ...

whatsapp-bot/                      ← NOVO: agrupa server.js, package.json, .wwebjs_auth
  server.js
  package.json

docs/                              ← NOVO: esta especificação e documentação futura
  product/ requirements/ architecture/ database/ security/ operations/ decisions/ learning/
```

## Explicação de cada diretório novo

- **`integrations/`**: existe porque a arquitetura de equipamentos (`architecture/equipamentos.md`) precisa de um lugar próprio para o driver e a factory — hoje esse código está espalhado em `services/isapi_poller.py` e dentro de `core/ronda_multi_nvr.py`; separar deixa explícito "isto é a fronteira com o mundo externo (Hikvision)".
- **`ai/`**: espelha a decisão de `architecture/ia.md` — separar "orquestração de ronda" (que continua em `core/`) de "decisão de qual modelo/regra rodar" (que passa a viver aqui).
- **`scripts/`**: os utilitários administrativos (`seed.py`, `limpar_rondas.py`, `debug_isapi.py`, `criar_tabela_nvr_monitorado.py`) já foram identificados como risco operacional quando soltos na raiz junto do código de produção (ver plano de correção/`decisions/decisoes-pendentes.md`) — mover para uma pasta própria deixa claro "isto não é parte do fluxo normal da aplicação".
- **`whatsapp-bot/`**: agrupa o que já é fisicamente separado (Node.js) — hoje `server.js`/`package.json` ficam soltos na raiz do repositório Python, misturando dois ecossistemas de dependência; agrupar não muda o comportamento, só a organização.
- **`docs/`**: onde este material vive — ver `decisions/documentacao.md` para a explicação completa da estrutura interna.

## O que **não** muda

`core/`, `models/`, `repositories/`, `services/`, `routes/`, `templates/`, `migrations/` continuam exatamente com o mesmo papel que já têm hoje — a proposta é aditiva (novos diretórios para novas responsabilidades), não uma reorganização do que já funciona.
