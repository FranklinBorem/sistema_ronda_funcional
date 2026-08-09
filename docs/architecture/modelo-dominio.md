# Modelo de Domínio — Vigilante IA

Modelagem **conceitual**: entidades de negócio antes de qualquer decisão de tabela/coluna. O modelo lógico do banco (`database/modelo-banco.md`) é derivado deste documento, não o contrário.

Para cada entidade: finalidade, atributos principais (conceituais, não tipos de coluna), relacionamentos, regras de negócio, e o mapeamento com o código atual.

---

### Empresa
- **Finalidade**: representa um cliente da plataforma (tenant).
- **Atributos principais**: nome, identificador único (slug), plano, status (ativa/suspensa).
- **Relacionamentos**: 1:N com Usuário, Unidade, Ocorrência, Integração, Auditoria.
- **Regras de negócio**: uma empresa suspensa não deve permitir login de seus usuários (exceto Super Admin, que atravessa empresas).
- **Existe hoje?** Não. **Model atual**: nenhum. **Ação**: **criar**.

### Usuário
- **Finalidade**: pessoa que acessa o sistema.
- **Atributos principais**: nome, credencial de login, papel, status (ativo/inativo).
- **Relacionamentos**: N:1 com Empresa; N:N com Unidade (para papéis de escopo restrito, via associação `UsuarioUnidade`).
- **Regras de negócio**: um usuário pertence a exatamente uma empresa (exceto Super Admin); a senha nunca é lida em texto plano, só verificada por hash.
- **Existe hoje?** Sim, parcialmente. **Model atual**: `models/monitor.py` (`Monitor`) — tem hash de senha correto (Werkzeug), mas não tem `empresa_id` nem `papel`. **Ação**: **modificar** (estender, não substituir — o hashing já está correto e não deve ser tocado).

### Papel
- **Finalidade**: define o que um usuário pode fazer (Super Admin, Admin da Empresa, Gestor, Supervisor, Operador, Visualizador).
- **Atributos principais**: nome, nível de permissão.
- **Relacionamentos**: um Usuário tem um Papel.
- **Regras de negócio**: hierarquia simples (não matriz de permissões granular no MVP) — ver `security/seguranca.md` para a justificativa dessa escolha.
- **Existe hoje?** Não. **Model atual**: nenhum. **Ação**: **criar** (como enum/campo em Usuário, não necessariamente tabela própria — decisão em `database/modelo-banco.md`).

### Unidade
- **Finalidade**: um site/local físico monitorado (ex.: uma usina, uma loja, um galpão).
- **Atributos principais**: nome, localização, status.
- **Relacionamentos**: N:1 com Empresa; 1:N com Área, NVR, Ronda.
- **Regras de negócio**: toda Unidade pertence a exatamente uma Empresa; equipamentos não podem existir sem Unidade.
- **Existe hoje?** Não como entidade. **Model atual**: campo texto `site` em `models/nvr.py` e `models/nvr_monitorado.py`. **Ação**: **criar** (e migrar o dado do campo texto para a nova entidade).

### Área
- **Finalidade**: subdivisão opcional dentro de uma Unidade (ex.: "Pátio de painéis", "Portaria").
- **Atributos principais**: nome.
- **Relacionamentos**: N:1 com Unidade; opcionalmente referenciada por NVR/Câmera.
- **Regras de negócio**: opcional — nem toda Unidade precisa de Área cadastrada.
- **Existe hoje?** Não. **Model atual**: nenhum. **Ação**: **criar**, mas como **Could Have** — não é bloqueio do MVP (ver `requirements/requisitos.md`).

### NVR
- **Finalidade**: o gravador/controlador que a plataforma se comunica para mover câmeras e consultar status.
- **Atributos principais**: fabricante, modelo, endereço de rede, credencial (referência, não a senha em si), status.
- **Relacionamentos**: N:1 com Unidade; 1:N com Câmera.
- **Regras de negócio**: a senha de acesso nunca deve ser exposta de volta à interface em texto plano (violação confirmada hoje em `templates/conferencia/nvr_form.html`).
- **Existe hoje?** Sim, de forma duplicada. **Model atual**: `models/nvr.py` (`Nvr`, para o fluxo de ronda/PTZ) e `models/nvr_monitorado.py` (`NvrMonitorado`, para o fluxo de conferência de disponibilidade) — **duas tabelas paralelas para o mesmo conceito de negócio**, sem FK entre si. **Ação**: **modificar/unificar** — candidato natural a consolidação na Fase 1, mas com cautela (ver risco em `decisions/decisoes-pendentes.md`, já que hoje servem fluxos operacionais distintos e ativos).

### Câmera
- **Finalidade**: um canal/câmera dentro de um NVR.
- **Atributos principais**: número do canal, nome, capacidades (PTZ, presets, captura, stream).
- **Relacionamentos**: N:1 com NVR; 1:N com Preset.
- **Regras de negócio**: nem toda câmera tem PTZ — hoje o sistema assume implicitamente que sim (ver `architecture/equipamentos.md`).
- **Existe hoje?** Parcialmente — hoje "câmera" é majoritariamente um número de canal dentro do NVR, sem entidade própria robusta com capacidades. **Model atual**: implícito em `models/nvr.py`/`NvrPreset` e nos campos de canal do `CameraStatusLog`. **Ação**: **modificar** — precisa ganhar o conceito explícito de capacidades.

### Preset
- **Finalidade**: uma posição PTZ pré-cadastrada para onde a câmera se move durante a ronda.
- **Atributos principais**: número do preset, nome/descrição.
- **Relacionamentos**: N:1 com Câmera/NVR.
- **Existe hoje?** Sim. **Model atual**: `models/nvr.py:NvrPreset`. **Ação**: **manter**.

### Configuração de Ronda
- **Finalidade**: define quais presets/câmeras uma ronda deve cobrir e, futuramente, agendamento.
- **Atributos principais**: unidade, lista de presets/câmeras envolvidas, agendamento (futuro).
- **Existe hoje?** Não como entidade separada — hoje a lista de NVRs/presets é montada dinamicamente a cada disparo (`services/ronda_service.py`). **Ação**: **criar**, como Should Have (agendamento é Could/Won't agora).

### Execução de Ronda
- **Finalidade**: o registro de uma ronda específica que rodou (ou está rodando).
- **Atributos principais**: status, início, fim, unidade, quem disparou.
- **Relacionamentos**: N:1 com Unidade e Usuário; 1:N com Resultado de Ronda.
- **Existe hoje?** Sim. **Model atual**: `models/ronda.py:Ronda`. **Ação**: **modificar** (ganha `unidade_id` no lugar de referência solta a NVR).

### Resultado de Ronda
- **Finalidade**: o resultado por NVR/câmera dentro de uma execução de ronda (sucesso, falha, imagens capturadas).
- **Existe hoje?** Sim. **Model atual**: `models/ronda.py:RondaNvr`. **Ação**: **manter**.

### Evento de IA
- **Finalidade**: uma detecção bruta gerada pelo motor de visão computacional (classe detectada, confiança, evidência).
- **Atributos principais**: câmera, modelo usado, classe, confiança, evidência (imagem), timestamp.
- **Relacionamentos**: N:1 com Câmera; opcionalmente gera uma Ocorrência.
- **Regras de negócio**: nem todo Evento de IA vira Ocorrência (depende da Regra de Detecção aplicada).
- **Existe hoje?** Parcialmente — hoje misturado com o conceito de Alerta (não separado em "detecção bruta" vs. "ocorrência a tratar"). **Model atual**: `models/alerta.py:Alerta`. **Ação**: **modificar/separar**.

### Regra de Detecção
- **Finalidade**: define o que fazer com uma detecção (qual modelo rodar, threshold, se gera ocorrência).
- **Atributos principais**: tipo de detecção, câmera/unidade alvo, parâmetros, ativo/inativo.
- **Existe hoje?** Não — hoje "detectar pessoa com YOLO" está hardcoded no motor de ronda (`core/ronda_multi_nvr.py`). **Ação**: **criar** (peça central da evolução de IA, ver `architecture/ia.md`).

### Ocorrência
- **Finalidade**: algo que aconteceu e precisa de tratativa humana — unifica o que hoje é `Alerta` (de IA) e `MonitorEvent` (de falha de equipamento).
- **Atributos principais**: origem, tipo, prioridade, status, responsável, evidência, tempos de resposta/resolução.
- **Relacionamentos**: N:1 com Empresa/Unidade; pode se originar de Evento de IA ou de falha de monitoramento.
- **Existe hoje?** Fragmentado. **Model atual**: `models/alerta.py:Alerta` (detecção IA) + `models/monitoring.py:MonitorEvent` (falha de equipamento) — dois modelos paralelos representando a mesma ideia de negócio de formas incompatíveis. **Ação**: **criar** (unificação), mantendo os dois modelos atuais como fontes de dado técnico, se necessário, por trás da nova entidade.

### Notificação
- **Finalidade**: registro do que foi efetivamente enviado (para auditoria de alertas — "o cliente foi avisado às 14:32 via Discord").
- **Existe hoje?** Não como registro — hoje o envio acontece (`discord_notification_service.py`, `email_service.py`) mas não fica um histórico consultável de notificações enviadas. **Ação**: **criar**, Should Have.

### Integração
- **Finalidade**: configuração de canal de notificação por empresa (Discord, e-mail, WhatsApp).
- **Existe hoje?** Não como entidade — hoje é configuração global do processo (`config.py`, variáveis de ambiente únicas para todo o sistema). **Ação**: **criar**.

### Auditoria
- **Finalidade**: log de quem fez o quê, quando, em qual empresa — ações administrativas sensíveis.
- **Existe hoje?** Não. **Ação**: **criar**, Should Have.

### Plano
- **Finalidade**: define limites/features disponíveis por empresa (nº câmeras, nº unidades).
- **Existe hoje?** Não. **Ação**: **criar**, Could Have — estrutura pronta para receber regra comercial futura, sem fechar o modelo de cobrança agora.
