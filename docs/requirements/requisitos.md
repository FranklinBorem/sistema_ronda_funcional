# Requisitos — Vigilante IA

Prioridade no formato MoSCoW: **Must Have** (sem isso não há MVP vendável), **Should Have** (fortalece, mas o primeiro cliente aceita sem), **Could Have** (bom ter, baixo custo de adiar), **Won't Have agora** (fora de escopo deliberadamente, não por esquecimento).

## Requisitos Funcionais

| # | Requisito | Prioridade | Motivo |
|---|---|---|---|
| RF01 | Cadastrar empresa (tenant) | Must | Sem isso não existe produto multi-cliente — é o requisito raiz de tudo mais |
| RF02 | Cadastrar usuário com papel | Must | Sem controle de quem acessa o quê, não há como vender a um segundo cliente com confiança |
| RF03 | Autenticar usuário (login/senha) | Must | Já existe (`routes/auth.py`) — requisito de continuidade, não novo |
| RF04 | Cadastrar unidade/site | Must | Hoje é texto livre (`site` em `models/nvr.py`); precisa virar entidade para permitir filtro/permissão confiáveis |
| RF05 | Cadastrar NVR | Must | Já existe (`routes/nvr.py`, `routes/conferencia_bp.py`) — precisa ganhar vínculo com unidade/empresa |
| RF06 | Cadastrar câmera/canal | Must | Já existe parcialmente (`NvrPreset`, canais do NVR) |
| RF07 | Configurar preset de câmera PTZ | Must | Já existe (`models/nvr.py:NvrPreset`) |
| RF08 | Executar ronda automatizada | Must | Funcionalidade central do produto — hoje quebrada por bug de invocação (ver plano de correção) |
| RF09 | Registrar resultado de ronda (com evidência) | Must | Já existe (`models/ronda.py`, `models/alerta.py`) |
| RF10 | Detectar evento por IA (pessoa) | Must | Já existe (YOLOv8 em `core/ronda_multi_nvr.py`) |
| RF11 | Gerar ocorrência a partir de evento | Should | Hoje existe de forma fragmentada (`Alerta`, `MonitorEvent`); unificação é melhoria, não bloqueio do primeiro cliente |
| RF12 | Tratar ocorrência (status, responsável, observações) | Should | Fortalece a proposta comercial, mas pode nascer simples |
| RF13 | Enviar notificação (Discord/e-mail/WhatsApp) | Should | Já existe globalmente; precisa virar configurável por empresa para ser Should e não Must |
| RF14 | Consultar dashboard de indicadores | Must | Já existe (`services/dashboard_service.py`) — precisa filtrar por empresa |
| RF15 | Monitorar disponibilidade de câmera/NVR | Must | Já existe (`services/isapi_poller.py`) |
| RF16 | Isolar dados entre empresas | Must | Requisito não-funcional com peso de funcional — sem isso, não há produto comercial seguro |
| RF17 | Auditar ações administrativas | Should | Esperado por clientes de segurança patrimonial que avaliam fornecedores tecnicamente, mas não bloqueia a primeira venda |
| RF18 | Suportar múltiplos tipos de detecção de IA | Won't agora | Fica para Fase 5 — abrir a estrutura (regra de detecção) é Must, implementar os tipos não é |
| RF19 | Suportar múltiplos fabricantes de equipamento | Won't agora | Idem — a abstração (driver) é Must, a segunda implementação não é |
| RF20 | Configurar planos/limites comerciais | Could | Só é urgente quando o modelo de cobrança for definido, o que você mesmo colocou como decisão futura |
| RF21 | Self-service de onboarding de novo cliente | Won't agora | No MVP, cadastro de nova empresa pode ser feito administrativamente (por você), sem tela de "criar minha conta" pública |
| RF22 | API pública para integração de terceiros | Won't agora | Fica para Fase 5 |

## Requisitos Não Funcionais

| # | Requisito | Prioridade | Motivo |
|---|---|---|---|
| RNF01 | Nenhum segredo em texto plano no código-fonte | Must | Vulnerabilidade confirmada hoje (webhook Discord hardcoded) — corrigível imediatamente, sem dependência de arquitetura |
| RNF02 | Senhas de usuário com hash seguro | Must | Já atendido (`werkzeug.security` em `models/monitor.py`) |
| RNF03 | Credenciais de equipamento (NVR) não armazenadas em texto plano | Must | Vulnerabilidade confirmada; MVP pode usar mitigação simples (ver `security/seguranca.md`), não precisa de cofre completo |
| RNF04 | Isolamento de dados entre empresas garantido em mais de uma camada | Must | É o requisito de maior risco de todo o produto — falhar aqui compromete a confiança de qualquer cliente |
| RNF05 | Proteção CSRF em formulários autenticados | Should | Real, mas pode esperar a estabilização de templates de tenant (evita retrabalho, já justificado no plano de correção) |
| RNF06 | Rate limiting / bloqueio de força bruta no login | Should | Mais crítico à medida que o sistema fica exposto publicamente para múltiplos clientes |
| RNF07 | Disponibilidade da aplicação (uptime) | Should | Importante para SLA comercial, mas o MVP para o primeiro cliente não exige alta disponibilidade formal (ex.: multi-AZ) |
| RNF08 | Desempenho do dashboard sob volume crescente | Could | Hoje resolvido por escala pequena; vira Must na Fase 4 (Escala) |
| RNF09 | Escalabilidade horizontal do motor de IA | Won't agora | Só relevante quando volume de clientes/câmeras justificar |
| RNF10 | Auditabilidade de configurações sensíveis | Should | Ligado a RF17 |
| RNF11 | Manutenibilidade (um único desenvolvedor consegue evoluir) | Must | Requisito pessoal seu, explícito na visão — pesa contra qualquer complexidade desnecessária (microserviços, frameworks pesados) |
| RNF12 | Observabilidade mínima (logs estruturados, erros capturados) | Must | Hoje ausente (`grep` não encontrou `@app.errorhandler` em lugar nenhum) — pré-requisito para depurar qualquer fase seguinte com segurança |
| RNF13 | Backup e recuperação do banco de dados | Must | Sem isso, qualquer erro de migration ou bug é irreversível — deve existir antes da Fase 0 avançar |
| RNF14 | Tempo de resposta do polling ISAPI não deve degradar a aplicação web | Could | Hoje já roda em thread separada (`services/conferencia_loop.py`), mitigação básica já existe |
