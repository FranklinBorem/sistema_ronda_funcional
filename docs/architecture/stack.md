# Stack Tecnológica — Avaliação

Critérios de recomendação, conforme pedido: tamanho da equipe (você, sozinho), sua capacidade de manutenção, estágio do produto, custo, ecossistema, facilidade de aprendizado, possibilidade de crescimento. **Nenhuma troca "porque é mais moderno" sem motivo concreto.**

| Tecnologia | Função | Situação atual | Alternativas | Recomendação |
|---|---|---|---|---|
| **Python** | Linguagem principal | Usado no backend inteiro, incluindo IA | Node.js, Go, Java | **Manter.** É a linguagem dominante em visão computacional/ML (PyTorch, Ultralytics) — trocar significaria perder acesso direto ao ecossistema de IA que o produto depende, sem ganho real |
| **Flask** | Framework web | `app.py` (Application Factory), blueprints organizados | Django, FastAPI | **Manter.** Django traria um ORM/admin próprios que colidiriam com o SQLAlchemy já usado; FastAPI é mais moderno para APIs assíncronas, mas o projeto é majoritariamente server-rendered (Jinja2), não uma API pura — a troca não se paga. Flask já demonstrou suportar bem a complexidade atual (blueprints, threads de background) |
| **SQLAlchemy** | ORM | Padrão moderno (`db.Mapped`, SQLAlchemy 2.x, confirmado em `requirements.txt`) | Django ORM, Tortoise, SQL puro | **Manter.** Já é a escolha mais madura do ecossistema Python para o nível de modelagem relacional que este produto precisa (FKs, relationships, migrations via Alembic) |
| **Alembic** | Migrations | Em uso, mas com lacuna confirmada (`nvr_monitorado` fora do controle de migration) | Migrations manuais, outra ferramenta | **Manter**, e usar de forma mais disciplinada (é uma questão de processo, não de ferramenta — Alembic já é a ferramenta certa, só precisa ser usada consistentemente) |
| **PostgreSQL** | Banco de dados | Já em uso (`config.py:postgresql+psycopg2`) | MySQL, SQLite (produção), NoSQL | **Manter.** Suporta nativamente Row-Level Security (decisivo para a estratégia de multi-tenancy recomendada em `database/multi-tenancy.md`), tipo `jsonb` (usado no modelo de banco para capacidades/parâmetros flexíveis), e é gratuito/open source — não há motivo técnico para trocar |
| **Node.js** | Runtime do bot WhatsApp | `server.js`, processo separado | Reescrever em Python | **Manter, isolado.** `whatsapp-web.js` não tem equivalente maduro em Python porque depende de automatizar o WhatsApp Web via navegador (Puppeteer) — é a ferramenta certa para essa tarefa específica, mesmo que introduza uma segunda linguagem no projeto |
| **whatsapp-web.js** | Integração WhatsApp | Em uso | API oficial do WhatsApp Business | **Avaliar migração no futuro, não agora.** A API oficial é mais estável/suportada, mas tem custo e processo de aprovação; `whatsapp-web.js` automatiza a versão web (mais frágil a mudanças do WhatsApp, mas gratuita) — adequado para MVP, reavaliar quando o produto tiver receita para justificar o custo da API oficial |
| **YOLO/Ultralytics** | Detecção de objetos | YOLOv8 em uso, com tiling customizado para câmeras distantes | YOLOv9/v10/v11, outros frameworks de detecção | **Manter YOLOv8 por ora.** É a versão já tunada/testada em campo (conforme as notas de otimização do projeto: tiling, FP16, dual-pass confidence); trocar de versão exigiria retestar tudo sem ganho comprovado para o caso de uso atual. Avaliar upgrade de versão como iniciativa própria, não como parte da reestruturação de produto |
| **PyTorch** | Backend de inferência do YOLO | Em uso via Ultralytics, com GPU (GTX 1650, conforme notas do projeto) | TensorFlow, ONNX Runtime | **Manter.** É dependência natural do Ultralytics; trocar não traria benefício e quebraria compatibilidade |
| **HTML/CSS/JS (Jinja2)** | Frontend | Server-rendered, sem framework JS | Ver `architecture/frontend.md` para análise dedicada | Ver documento específico |

## Observação sobre `requirements.txt` e `package.json`

Já identificado no plano de correção: `psycopg2-binary` ausente de `requirements.txt` apesar de necessário — isso não é uma questão de "qual tecnologia usar", é uma lacuna de manutenção da lista de dependências da tecnologia já escolhida corretamente. Corrigir isso é Fase 0, não uma decisão de stack.

## Resumo

Nenhuma troca de tecnologia central é recomendada. O maior valor está em **usar melhor** o que já existe (Alembic de forma disciplinada, PostgreSQL com RLS) do que trocar por algo novo. Isso é coerente com sua capacidade de manutenção como desenvolvedor único: aprender a fundo uma stack já dominada tem mais retorno do que espalhar esforço aprendendo uma stack nova sem necessidade comprovada.
