# Visão do Produto — Vigilante IA

## Problema que o produto resolve

Centros de monitoramento CFTV e empresas de segurança patrimonial hoje dependem fortemente de **operadores humanos olhando telas** para: perceber que uma câmera caiu, perceber uma pessoa em local restrito, e registrar manualmente o que aconteceu (geralmente em planilha ou papel). Isso tem três consequências observáveis no próprio histórico deste projeto (antes de virar Flask, era controlado por planilha — `Relatorio_Ronda_GrupoRonda.xlsx`, citado nas notas do projeto): baixa cobertura (um operador não consegue olhar 100 câmeras ao mesmo tempo), inconsistência de registro (cada operador documenta diferente) e ausência de indicadores confiáveis (não dá para calcular SLA de uma planilha preenchida manualmente).

O Vigilante IA resolve isso automatizando três coisas que hoje são manuais: **movimentação e inspeção de câmeras (ronda)**, **verificação de que o equipamento está funcionando (disponibilidade)** e **detecção de eventos por visão computacional**, com registro estruturado em banco de dados em vez de planilha.

## Público-alvo

- Empresas de segurança patrimonial que operam centros de monitoramento CFTV para terceiros.
- Empresas que possuem CFTV próprio para proteger seus próprios ativos (ex.: usinas fotovoltaicas, como é o caso de origem do projeto).
- Organizações com múltiplos locais/unidades geograficamente distribuídas, cada uma com câmeras/NVRs próprios.

**Fora do público-alvo, por ora**: consumidores finais (CFTV residencial) — o produto pressupõe operação profissional com equipe de monitoramento, não uma pessoa olhando o próprio celular.

## Personas (hipotéticas, para orientar decisões de produto — não são usuários reais entrevistados)

| Persona | Papel | O que essa pessoa precisa do sistema |
|---|---|---|
| **Marcos**, gestor de operações de uma empresa de segurança | Contrata/decide comprar o produto | Dashboard com disponibilidade de câmeras e indicadores de SLA — ele responde para o cliente final dele sobre isso |
| **Fernanda**, operadora de central de monitoramento | Usa o sistema no dia a dia | Disparar rondas, ver alertas, tratar ocorrências rapidamente — não pode ser um sistema lento nem confuso |
| **Diego**, técnico de CFTV | Cadastra e mantém os equipamentos | Cadastrar NVR/câmera/preset de forma confiável; precisa saber quando um equipamento está com problema antes do cliente reclamar |
| **Você (Franklin)**, hoje desenvolvedor único | Mantém e evolui o sistema | Um sistema que ele consegue entender e manter sozinho — este ponto pesa diretamente nas decisões de stack e arquitetura ao longo deste documento |

## Proposta de valor

Reduzir a dependência de olhos humanos constantemente colados em tela, substituindo por: rondas automáticas com IA cobrindo pontos cegos, alertas de indisponibilidade de equipamento antes que o cliente perceba, e um histórico estruturado que gera indicadores de verdade (não estimativa de planilha).

## Principais diferenciais (frente ao que existe hoje no mercado, com base na análise competitiva já feita — Grupo Ronda vs. Monuv, citada nas notas do projeto)

- Automação de ronda com PTZ + IA, não só gravação passiva.
- Monitoramento de saúde de equipamento como produto próprio (não só "a câmera grava ou não"), incluindo métricas como HDD e bitrate do NVR.
- Preço historicamente competitivo (R$ 36/câmera monitorada, praticado hoje) frente a soluções de VMS em nuvem.

## Principais casos de uso (visão de negócio, não técnica — o detalhamento técnico está em `architecture/casos-de-uso.md`)

1. Executar ronda automatizada e revisar o relatório gerado.
2. Ser avisado quando uma câmera/NVR fica indisponível, sem precisar checar manualmente.
3. Receber um alerta quando a IA detecta algo relevante (hoje: pessoa em local/horário incomum).
4. Consultar um dashboard de indicadores da operação.
5. (Comercial) Uma empresa cliente cadastra suas próprias unidades/equipamentos e opera de forma isolada de outros clientes.

## Limites do produto — o que ele NÃO faz

- Não é um VMS (Video Management System) completo — não substitui a gravação contínua/NVR do cliente; ele **consulta** o NVR existente, não grava vídeo por conta própria.
- Não é um sistema de controle de acesso (catracas, biometria) — pode futuramente **integrar** com um, mas não substitui.
- Não faz atendimento/despacho de emergência (não liga para a polícia) — gera ocorrência para um humano tratar.
- Não é uma plataforma de CFTV residencial/consumidor.

---

## Produto atual (o que o sistema já faz, confirmado por leitura do código)

- Cadastro de NVRs/câmeras/presets, com credenciais de acesso (`models/nvr.py`, `models/nvr_monitorado.py`).
- Ronda automatizada: move PTZ para presets cadastrados, tira snapshot, roda YOLOv8 para detectar pessoas, grava alerta se detectar (`core/ronda_multi_nvr.py`), gera relatório.
- Conferência de câmeras: polling periódico via protocolo ISAPI (Hikvision) verificando status de canal/HD/bitrate, com abertura/fechamento de "eventos" de falha (`services/isapi_poller.py`, `services/conferencia_loop.py`).
- Notificações via Discord e e-mail (`services/discord_notification_service.py`, `services/email_service.py`), e leitura de mensagens de grupos de WhatsApp relacionados à operação (`server.js` + `routes/whatsapp.py`).
- Login single-tenant (um único conjunto de usuários, sem conceito de empresa/cliente).
- Dashboard com KPIs básicos (rondas do dia, tempo médio, câmeras indisponíveis) — `services/dashboard_service.py`.

## Produto desejado (o que queremos que ele passe a fazer — ainda não existe)

- Suportar múltiplas empresas clientes isoladas entre si (multi-tenant).
- Papéis de usuário com diferentes níveis de acesso.
- Ocorrências como conceito unificado (hoje fragmentado entre "alerta de IA" e "evento de indisponibilidade").
- Estrutura hierárquica real (Empresa → Unidade → Área → NVR → Câmera), não campos de texto livre.
- Camada de abstração de equipamento que não pressuponha Hikvision.
- Arquitetura de IA que suporte novos tipos de detecção sem alterar o núcleo do motor de ronda.

## Visão futura (o que poderá vir depois, não faz parte do MVP)

- Múltiplos fabricantes de NVR/câmera além de Hikvision.
- Múltiplos tipos de detecção de IA (veículo, invasão de área, permanência, aglomeração, objeto abandonado).
- Billing/planos comerciais automatizados.
- Integrações com controle de acesso e sistemas de alarme de terceiros.
- API pública para clientes integrarem com seus próprios sistemas.
- App mobile dedicado (hoje é web responsivo, na melhor das hipóteses).
