# Fluxos Principais — Diagramas de Sequência

## Fluxo 1 — Login

```mermaid
sequenceDiagram
    actor U as Usuario
    participant R as Routes (auth.py)
    participant Rep as MonitorRepository
    participant M as Model Usuario
    participant S as Sessao Flask

    U->>R: POST /login (usuario, senha)
    R->>Rep: buscar_por_usuario(usuario)
    Rep-->>R: registro do usuario (ou nada)
    R->>M: verificar_senha(senha)
    M-->>R: valido / invalido
    alt valido
        R->>S: session[usuario_id] = id, session[empresa_id] = ..., session[papel] = ...
        R-->>U: redireciona ao dashboard
    else invalido
        R-->>U: erro de credenciais
    end
```

**Estado atual vs. alvo**: hoje `session` só carrega `monitor_id` (`routes/auth.py`, `core/auth.py`). O alvo acrescenta `empresa_id` e `papel`, sem trocar o mecanismo de sessão em si.

## Fluxo 2 — Cadastro de equipamento

```mermaid
sequenceDiagram
    actor A as Admin da Empresa
    participant R as Routes
    participant S as Service
    participant Rep as Repository
    participant DB as PostgreSQL

    A->>R: cadastrar Unidade
    R->>S: criar_unidade(empresa_id, dados)
    S->>Rep: salvar
    Rep->>DB: INSERT unidades
    A->>R: cadastrar NVR (vinculado a unidade)
    R->>S: criar_nvr(unidade_id, credenciais)
    S->>Rep: salvar (credencial via referencia de segredo)
    Rep->>DB: INSERT nvrs
    A->>R: cadastrar Cameras/Canais
    R->>S: criar_camera(nvr_id, canal, capacidades)
    S->>Rep: salvar
    A->>R: cadastrar Presets
    R->>S: criar_preset(camera_id, numero)
    S->>Rep: salvar
```

**Estado atual**: já existe fluxo equivalente para NVR/preset (`routes/nvr.py`, `routes/conferencia_bp.py`), mas sem a etapa de Unidade nem vínculo com empresa.

## Fluxo 3 — Execução de ronda

```mermaid
sequenceDiagram
    actor U as Usuario/Agendamento
    participant R as Routes (rondas.py)
    participant RS as RondaService
    participant Motor as core.ronda_multi_nvr
    participant NVR as NVR (ISAPI)
    participant IA as Motor de Deteccao
    participant Rep as Repositories
    participant DB as PostgreSQL

    U->>R: POST /iniciar_ronda_multi
    R->>RS: iniciar_ronda_multi(unidade_id)
    RS->>Rep: criar Ronda (status=em_andamento)
    Rep->>DB: INSERT rondas
    RS->>Motor: dispara em thread: executar_ronda_multi(ronda_id)
    R-->>U: resposta imediata (ronda iniciada)

    loop para cada NVR/camera/preset
        Motor->>NVR: mover PTZ para preset
        Motor->>NVR: capturar snapshot
        Motor->>IA: analisar imagem (regra de deteccao)
        IA-->>Motor: eventos detectados
        Motor->>Rep: salvar EventoIA / ResultadoRonda
        alt evento relevante
            Motor->>Rep: gerar Ocorrencia
        end
    end

    Motor->>Rep: atualizar Ronda (status final)
    Rep->>DB: UPDATE rondas
```

**Estado atual**: o disparo hoje usa `subprocess.Popen` apontando para um caminho de script inexistente (bug confirmado, ver plano de correção) — o diagrama já reflete a correção recomendada (chamada direta em thread a `executar_ronda_multi`), não o comportamento quebrado atual.

## Fluxo 4 — Conferência de câmera

```mermaid
sequenceDiagram
    participant Sch as Scheduler (thread daemon)
    participant Poller as IsapiPoller
    participant NVR as NVR (ISAPI)
    participant Rep as Repositories
    participant DB as PostgreSQL
    participant Dash as Dashboard

    loop a cada N segundos
        Sch->>Poller: consultar status de todos os NVRs ativos
        Poller->>NVR: GET /ISAPI/... (status canal, HD, bitrate)
        NVR-->>Poller: resposta ISAPI
        Poller->>Rep: gravar NvrStatusLog / CameraStatusLog
        Rep->>DB: INSERT
        alt equipamento indisponivel
            Poller->>Rep: abrir/atualizar MonitorEvent
            Rep->>Rep: pode gerar Ocorrencia
        end
    end
    Dash->>Rep: consultar disponibilidade agregada
    Rep-->>Dash: indicadores
```

**Estado atual**: já funciona essencialmente assim (`services/conferencia_loop.py`, `services/isapi_poller.py`), com a ressalva já mapeada da duplicidade com `conferencia_loop.py` na raiz do projeto (ver plano de correção).

## Fluxo 5 — Ocorrência

```mermaid
sequenceDiagram
    participant Ev as Evento (IA ou falha equipamento)
    participant Reg as Regra (deteccao ou monitoramento)
    participant Oc as Modulo Ocorrencia
    actor Resp as Responsavel
    participant DB as PostgreSQL

    Ev->>Reg: avaliar criterio (threshold, severidade)
    alt atende criterio
        Reg->>Oc: criar Ocorrencia (status=aberta)
        Oc->>DB: INSERT ocorrencias
        Oc->>Resp: notificar (via modulo de notificacao)
        Resp->>Oc: assumir/tratar (status=em_tratamento)
        Resp->>Oc: registrar observacoes
        Resp->>Oc: encerrar (status=resolvida, tratado_em=now)
        Oc->>DB: UPDATE ocorrencias
    else nao atende criterio
        Reg-->>Ev: descarta (fica so como EventoIA/log, sem virar ocorrencia)
    end
```

**Estado atual**: fragmentado — hoje um `Alerta` (de IA) não passa por esse ciclo de tratativa formal; um `MonitorEvent` (de equipamento) tem abertura/fechamento automático, mas não tratativa humana estruturada. Este fluxo representa o estado-alvo pós-unificação.

## Fluxo 6 — Notificação

```mermaid
sequenceDiagram
    participant Oc as Ocorrencia
    participant NotifMod as Modulo Notificacao
    participant Int as Integracao (config por empresa)
    participant Canal as Discord/E-mail/WhatsApp
    participant DB as PostgreSQL

    Oc->>NotifMod: notificar(ocorrencia)
    NotifMod->>Int: resolver configuracao da empresa
    Int-->>NotifMod: webhook/SMTP/token configurado
    NotifMod->>Canal: enviar mensagem
    Canal-->>NotifMod: confirmacao/erro
    NotifMod->>DB: registrar em Notificacao (enviado_em, status_envio)
```

**Estado atual**: hoje o envio existe (`discord_notification_service.py`, `email_service.py`) mas resolve a configuração de forma global (`app.config`), não por empresa, e não fica registro consultável do que foi enviado — ambos os pontos fazem parte da evolução descrita aqui.
