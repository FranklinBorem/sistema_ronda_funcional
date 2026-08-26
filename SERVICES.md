"""Camada de serviços da aplicação Flask."""

from .dashboard_service import DashboardService
from .email_service import EmailService, EnvioEmail, FiltroEmail
from .ronda_service import RondaService
from .whatsapp_service import WhatsAppMonitorService

__all__ = [
    "DashboardService",
    "EmailService",
    "EnvioEmail",
    "FiltroEmail",
    "RondaService",
    "WhatsAppMonitorService",
]

"""
services/conferencia_loop.py — Grupo Ronda · Loop de coleta de status

Roda em background (thread daemon) e salva no banco a cada INTERVALO_SEGUNDOS.
Popula três tabelas:
  - nvr_status_log      → uma linha por NVR por polling
  - camera_status_log   → uma linha por câmera por polling
  - monitor_event       → abre/fecha eventos de falha automaticamente

Inicialização em app.py:
    from services.conferencia_loop import iniciar_loop
    iniciar_loop(app)
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 300   # 5 minutos — ajuste conforme necessário


def _executar_polling(app):
    """Executa um ciclo completo de polling e salva no banco."""
    from extensions import db
    from models.nvr_monitorado import NvrMonitorado
    from models.nvr_status_log import NvrStatusLog
    from models.monitoring import CameraStatusLog, MonitorEvent
    from services.isapi_poller import ConferenceManager, NvrConfig

    with app.app_context():
        try:
            nvrs_db = NvrMonitorado.query.filter_by(ativo=True).all()
            if not nvrs_db:
                logger.debug("conferencia_loop: nenhum NVR ativo para pollar")
                return

            configs = [
                NvrConfig(
                    nvr_id=n.nvr_id, name=n.nome, host=n.ip,
                    port=n.porta, username=n.usuario,
                    password=n.senha, use_https=n.use_https,
                )
                for n in nvrs_db
            ]

            manager = ConferenceManager(configs, workers=4, timeout=10)
            results = manager.poll_all()
            agora = datetime.utcnow()

            for nvr in results:
                # ── 1. NvrStatusLog ────────────────────────────────────────
                log = NvrStatusLog(
                    nvr_id=nvr.nvr_id,
                    nvr_nome=nvr.name,
                    timestamp=agora,
                    health=nvr.health_label,
                    reachable=nvr.reachable,
                    cameras_total=nvr.cameras_total,
                    cameras_online=nvr.cameras_online,
                    cameras_offline=nvr.cameras_offline,
                    erro=nvr.error or None,
                )
                db.session.add(log)

                # ── 2. CameraStatusLog ─────────────────────────────────────
                for cam in nvr.cameras:
                    db.session.add(CameraStatusLog(
                        nvr_id=nvr.nvr_id,
                        channel_id=cam.channel_id,
                        channel_name=cam.channel_name or f"Canal {cam.channel_id}",
                        timestamp=agora,
                        online=cam.online,
                        signal_ok=cam.signal_ok,
                        recording=cam.recording,
                        bit_rate_kbps=cam.bit_rate_kbps,
                    ))

                # ── 3. MonitorEvent — NVR inacessível ─────────────────────
                _gerenciar_evento_nvr(db, nvr, agora)

                # ── 4. MonitorEvent — câmeras offline ─────────────────────
                for cam in nvr.cameras:
                    _gerenciar_evento_camera(db, nvr.nvr_id, cam, agora)

            db.session.commit()
            logger.info(f"conferencia_loop: polling OK — {len(results)} NVR(s)")

        except Exception:
            logger.exception("conferencia_loop: erro durante polling")
            try:
                db.session.rollback()
            except Exception:
                pass


def _gerenciar_evento_nvr(db, nvr, agora: datetime):
    """Abre ou fecha evento de NVR inacessível/em atenção."""
    from models.monitoring import MonitorEvent

    chave = "nvr_inacessivel" if not nvr.reachable else "nvr_atencao"
    ha_problema = not nvr.reachable or nvr.health_label == "ATENÇÃO"

    # Evento ativo existente para este NVR
    evento_ativo = MonitorEvent.query.filter_by(
        nvr_id=nvr.nvr_id,
        alvo_tipo="nvr",
        resolvido_em=None,
    ).first()

    if ha_problema:
        if not evento_ativo:
            db.session.add(MonitorEvent(
                alvo_tipo="nvr",
                nvr_id=nvr.nvr_id,
                nome_exibicao=nvr.name,
                severidade="critica" if not nvr.reachable else "media",
                chave_problema=chave,
                mensagem=f"NVR '{nvr.name}' {nvr.health_label}. {nvr.error or ''}".strip(),
                aberto_em=agora,
            ))
    else:
        if evento_ativo:
            evento_ativo.resolvido_em = agora


def _gerenciar_evento_camera(db, nvr_id: str, cam, agora: datetime):
    """Abre ou fecha evento de câmera offline."""
    from models.monitoring import MonitorEvent

    if not cam.online:
        evento = MonitorEvent.query.filter_by(
            nvr_id=nvr_id,
            channel_id=cam.channel_id,
            alvo_tipo="camera",
            resolvido_em=None,
        ).first()
        if not evento:
            db.session.add(MonitorEvent(
                alvo_tipo="camera",
                nvr_id=nvr_id,
                channel_id=cam.channel_id,
                nome_exibicao=cam.channel_name or f"Canal {cam.channel_id}",
                severidade="alta",
                chave_problema="camera_offline",
                mensagem=f"Câmera '{cam.channel_name}' offline (canal {cam.channel_id})",
                aberto_em=agora,
            ))
    else:
        # Fecha evento se estava aberto
        evento = MonitorEvent.query.filter_by(
            nvr_id=nvr_id,
            channel_id=cam.channel_id,
            alvo_tipo="camera",
            resolvido_em=None,
        ).first()
        if evento:
            evento.resolvido_em = agora


def _loop(app):
    """Thread principal do loop."""
    logger.info(f"conferencia_loop: iniciado (intervalo={INTERVALO_SEGUNDOS}s)")
    while True:
        _executar_polling(app)
        time.sleep(INTERVALO_SEGUNDOS)


def iniciar_loop(app):
    """
    Inicia o loop de coleta em thread daemon.
    Chamar UMA VEZ em app.py após create_app().

    Exemplo:
        from services.conferencia_loop import iniciar_loop
        iniciar_loop(app)
    """
    t = threading.Thread(target=_loop, args=(app,), daemon=True, name="conferencia_loop")
    t.start()
    logger.info("conferencia_loop: thread daemon iniciada")

"""
services/dashboard_service.py — Dados do dashboard principal.

Responsabilidade única: montar o dicionário de contexto que a rota
/dashboard entrega ao template. Toda persistência é delegada a
AlertaRepository, RondaRepository e NvrRepository.

Não importa sqlite3, get_db, nvr_config nem queries SQL — apenas repositórios.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from repositories.alerta_repository import AlertaRepository
from repositories.nvr_repository import NvrRepository
from repositories.ronda_repository import RondaRepository


class DashboardService:
    """Monta os dados do dashboard sem acoplar regra de negócio ao Flask."""

    def __init__(
        self,
        dias: int = 30,
        alerta_repo: AlertaRepository | None = None,
        ronda_repo: RondaRepository | None = None,
        nvr_repo: NvrRepository | None = None,
    ) -> None:
        self.dias = dias
        self._alerta_repo = alerta_repo or AlertaRepository()
        self._ronda_repo  = ronda_repo  or RondaRepository()
        self._nvr_repo    = nvr_repo    or NvrRepository()

    # ── API pública ────────────────────────────────────────────────────────

    def build_context(self) -> dict:
        rondas = self._ronda_repo.listar_historico(limite=20)
        return {
            "rondas": rondas,
            "kpi":    self._build_kpis(),
            "dias":   self.dias,
        }

    # ── KPIs ───────────────────────────────────────────────────────────────

    def _build_kpis(self) -> dict:
        return {
            **self._build_ronda_kpis(),
            **self._build_alerta_kpis(),
            "nvrs_ativos": self._nvr_repo.listar(apenas_ativos=True).__len__(),
        }

    def _build_ronda_kpis(self) -> dict:
        por_status  = self._ronda_repo.contar_por_status()
        total       = sum(por_status.values())
        ok          = por_status.get("finalizada", 0)
        alerta      = por_status.get("com_alertas", 0)
        hoje        = datetime.utcnow().strftime("%Y-%m-%d")
        rondas_hoje = len(self._ronda_repo.listar_filtrado(data_ini=hoje, limite=9999))

        return {
            "rondas_total":    total,
            "rondas_ok":       ok,
            "rondas_alerta":   alerta,
            "rondas_hoje":     rondas_hoje,
            "tempo_medio_min": self._tempo_medio_ronda(),
        }

    def _build_alerta_kpis(self) -> dict:
        try:
            resumo   = self._alerta_repo.resumo()
            top_nvrs = self._top_nvrs_formatado()
            labels, valores = self._grafico_ultimos_dias()
        except Exception:
            resumo   = {"total": 0, "pendentes": 0, "tratados": 0, "deteccoes_falsas": 0}
            top_nvrs = []
            labels, valores = [], []

        total       = resumo["total"]
        confirmados = resumo["tratados"]
        falsas      = resumo["deteccoes_falsas"]
        precisao    = round(confirmados / total * 100) if total else 0

        return {
            "det_total":       total,
            "det_pendente":    resumo["pendentes"],
            "det_tratando":    falsas,
            "det_tratado":     confirmados,
            "confirmados":     confirmados,
            "falsos_positivos": falsas,
            "precisao":        precisao,
            "top_nvrs":        top_nvrs,
            "grafico_labels":  labels,
            "grafico_valores": valores,
        }

    # ── Helpers ────────────────────────────────────────────────────────────

    def _tempo_medio_ronda(self) -> float:
        corte  = (datetime.utcnow() - timedelta(days=self.dias)).strftime("%Y-%m-%d")
        rondas = self._ronda_repo.listar_filtrado(data_ini=corte, status="finalizada", limite=9999)
        diffs  = [
            (r.finalizada_em - r.iniciada_em).total_seconds() / 60
            for r in rondas
            if r.iniciada_em and r.finalizada_em
        ]
        return round(sum(diffs) / len(diffs), 1) if diffs else 0.0

    def _top_nvrs_formatado(self) -> list[dict]:
        rows = self._alerta_repo.top_nvrs_alertas(dias=self.dias, limite=5)
        if not rows:
            return []
        max_total = rows[0]["total"] or 1
        return [
            {"nome": r["nvr"], "total": r["total"], "pct": round(r["total"] / max_total * 100)}
            for r in rows
        ]

    def _grafico_ultimos_dias(self) -> tuple[list[str], list[int]]:
        rows   = self._alerta_repo.alertas_por_dia(dias=14)
        por_dia: dict[str, int] = {r["dia"]: r["total"] for r in rows}
        labels, valores = [], []
        for i in range(13, -1, -1):
            data = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            labels.append(data[5:])
            valores.append(por_dia.get(data, 0))
        return labels, valores

"""
services/discord_notification_service.py — Grupo Ronda · Alertas via Discord

Envia embeds formatados para um webhook do Discord quando:
  - Um NVR fica inacessível / entra em atenção
  - Uma câmera fica offline / perde sinal
  - Um evento é resolvido

Configuração em config.py / .env:
    DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520976634218287155/QNDrNhBrciw3NEe_AgefFnu3OkBCIawMXdj8HpSbUIfCIumhnoQFK_T8c4xweFnaXO7b"
    DISCORD_WEBHOOK_ENABLED = True          # False para silenciar sem remover a config
    DISCORD_MENTION_ROLE_ID = "123456789"   # opcional: @role a mencionar em alertas críticos

Uso independente (sem Flask, para testes):
    from services.discord_notification_service import DiscordNotificationService
    svc = DiscordNotificationService(webhook_url="https://discord.com/...")
    svc.enviar_teste()
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ── Paleta de cores Discord (decimal) ──────────────────────────────────────
_COR = {
    "critica":  0xE84057,   # vermelho
    "alta":     0xF97316,   # laranja
    "media":    0xF5C400,   # dourado Ronda
    "baixa":    0x3B82F6,   # azul
    "ok":       0x22C55E,   # verde (resolução)
}

_EMOJI = {
    "critica":          "🔴",
    "alta":             "🟠",
    "media":            "🟡",
    "baixa":            "🔵",
    "ok":               "✅",
    "nvr_inacessivel":  "📡",
    "nvr_atencao":      "⚠️",
    "camera_offline":   "📷",
    "camera_sem_sinal": "📵",
}


class DiscordNotificationService:
    """
    Envia notificações de eventos de monitoramento via Discord Webhook.
    Pode ser usada em paralelo ou em substituição ao MonitorNotificationService (e-mail).
    """

    def __init__(
        self,
        webhook_url: str | None = None,
        enabled: bool = True,
        mention_role_id: str | None = None,
    ):
        self.webhook_url = webhook_url
        self.enabled = enabled
        self.mention_role_id = mention_role_id  # ex: "123456789012345678"

    # ── API pública ──────────────────────────────────────────────────────────

    def notificar_novos_eventos(self, eventos: list) -> None:
        """Recebe lista de MonitorEvent e notifica cada um."""
        for evento in eventos:
            self._notificar_evento(evento, resolucao=False)

    def notificar_resolucao(self, evento) -> None:
        self._notificar_evento(evento, resolucao=True)

    def enviar_teste(self) -> bool:
        """Envia uma mensagem de teste ao webhook. Retorna True se OK."""
        payload = {
            "username": "Vigilante IA · Grupo Ronda",
            "embeds": [{
                "title": "✅ Webhook configurado com sucesso",
                "description": (
                    "O sistema de alertas do **Vigilante IA** está conectado.\n"
                    f"Horário do teste: `{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}`"
                ),
                "color": _COR["ok"],
                "footer": {"text": "Grupo Ronda · Vigilante IA"},
            }],
        }
        return self._post(payload)

    # ── Internos ─────────────────────────────────────────────────────────────

    def _notificar_evento(self, evento, resolucao: bool) -> None:
        if not self.enabled or not self.webhook_url:
            logger.debug("Discord: notificações desabilitadas ou webhook não configurado.")
            return

        try:
            payload = self._montar_payload(evento, resolucao)
            ok = self._post(payload)
            if ok:
                evento.notificado = True
        except Exception:
            logger.exception(f"Discord: falha ao notificar evento #{getattr(evento, 'id', '?')}")

    def _montar_payload(self, evento, resolucao: bool) -> dict[str, Any]:
        chave      = getattr(evento, "chave_problema", "")
        severidade = getattr(evento, "severidade", "media")
        nome       = getattr(evento, "nome_exibicao", "Dispositivo desconhecido")
        mensagem   = getattr(evento, "mensagem", "")
        aberto_em  = getattr(evento, "aberto_em", None)
        resolvido  = getattr(evento, "resolvido_em", None)

        if resolucao:
            cor    = _COR["ok"]
            emoji  = _EMOJI["ok"]
            titulo = f"RESOLVIDO — {nome}"
            status_linha = f"**Status:** ✅ Resolvido às `{resolvido.strftime('%H:%M:%S') if resolvido else 'agora'}`"
        else:
            cor    = _COR.get(severidade, _COR["media"])
            emoji  = _EMOJI.get(chave, _EMOJI.get(severidade, "⚠️"))
            titulo = f"{emoji} ALERTA — {nome}"
            status_linha = f"**Severidade:** {severidade.upper()}"

        # Duração só disponível se resolvido
        duracao_linha = ""
        if resolucao and aberto_em and resolvido:
            delta = resolvido - aberto_em
            minutos = int(delta.total_seconds() // 60)
            duracao_linha = f"\n**Duração do problema:** `{minutos} min`"

        desc_parts = [
            mensagem,
            "",
            status_linha,
            f"**Tipo:** `{chave}`" if chave else "",
            f"**Aberto em:** `{aberto_em.strftime('%d/%m/%Y %H:%M:%S') if aberto_em else 'agora'}`",
            duracao_linha,
        ]
        description = "\n".join(p for p in desc_parts if p is not None)

        embed: dict[str, Any] = {
            "title":       titulo,
            "description": description,
            "color":       cor,
            "timestamp":   datetime.utcnow().isoformat(),
            "footer":      {"text": "Grupo Ronda · Vigilante IA"},
        }

        # Mention @role apenas em alertas críticos (não em resoluções)
        content = ""
        if not resolucao and severidade == "critica" and self.mention_role_id:
            content = f"<@&{self.mention_role_id}>"

        return {
            "username":   "Vigilante IA · Grupo Ronda",
            "avatar_url": "https://i.imgur.com/4M34hi2.png",  # substitua pelo logo da Ronda
            "content":    content,
            "embeds":     [embed],
        }

    def _post(self, payload: dict) -> bool:
        if not self.webhook_url:
            logger.warning("Discord: DISCORD_WEBHOOK_URL não configurado.")
            return False
        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code in (200, 204):
                return True
            logger.warning(f"Discord webhook retornou {resp.status_code}: {resp.text[:200]}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Discord: erro de rede ao enviar webhook: {e}")
            return False


# ── Factory helper para uso dentro do Flask ────────────────────────────────

def make_discord_service_from_app(app) -> DiscordNotificationService:
    """
    Constrói DiscordNotificationService a partir das config do Flask.
    Chame dentro de app_context.

    Exemplo em conferencia_loop.py:
        discord = make_discord_service_from_app(app)
    """
    return DiscordNotificationService(
        webhook_url=app.config.get("DISCORD_WEBHOOK_URL"),
        enabled=app.config.get("DISCORD_WEBHOOK_ENABLED", True),
        mention_role_id=app.config.get("DISCORD_MENTION_ROLE_ID"),
    )

"""
services/email_service.py — Envio de e-mails de relatório de ronda.

Responsabilidades:
  - Montar o contexto de filtro/listagem para a rota /email
  - Renderizar o corpo HTML do e-mail a partir de um template Jinja2
  - Enviar via SMTP com anexo de imagens (multipart/related)
  - Registrar o envio no log de auditoria (opcional, extensível)

Não importa sqlite3 nem queries SQL — apenas RondaRepository e
MonitorRepository.

Configuração SMTP esperada em config.py (ou variáveis de ambiente):
    MAIL_SERVER   = "smtp.example.com"
    MAIL_PORT     = 587
    MAIL_USE_TLS  = True
    MAIL_USERNAME = "vigilante@example.com"
    MAIL_PASSWORD = "secret"
    MAIL_SENDER   = "Vigilante IA <vigilante@example.com>"
    MAIL_DEFAULT_RECEIVER = "seguranca@example.com"
"""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from flask import current_app, render_template

from repositories.monitor_repository import MonitorRepository
from repositories.ronda_repository import RondaRepository


# ── Tipos de dados ─────────────────────────────────────────────────────────

@dataclass
class FiltroEmail:
    """Parâmetros de filtro vindos do formulário da rota /email."""
    data_ini: str | None = None
    data_fim: str | None = None
    turno: str | None = None
    monitor_nome: str | None = None
    status: str | None = None


@dataclass
class EnvioEmail:
    """Parâmetros do envio vindo do formulário da rota /email/enviar."""
    destinatario: str
    ronda_ids: list[int] = field(default_factory=list)
    assunto: str = "Relatório de Ronda — Vigilante IA"
    incluir_imagens: bool = True


# ── Service ────────────────────────────────────────────────────────────────

class EmailService:
    """Monta e envia e-mails de relatório de ronda."""

    def __init__(
        self,
        ronda_repo: RondaRepository | None = None,
        monitor_repo: MonitorRepository | None = None,
    ) -> None:
        self._ronda_repo = ronda_repo or RondaRepository()
        self._monitor_repo = monitor_repo or MonitorRepository()

    # ── Contexto para a rota /email ────────────────────────────────────────

    def montar_contexto_listagem(self, filtro: FiltroEmail) -> dict[str, Any]:
        """
        Retorna o dicionário de contexto para o template email_listagem.html.
        Inclui as rondas filtradas e as opções dos selects de filtro.
        """
        rondas = self._ronda_repo.listar_filtrado(
            data_ini=filtro.data_ini,
            data_fim=filtro.data_fim,
            turno=filtro.turno,
            monitor_nome=filtro.monitor_nome,
            status=filtro.status,
        )
        monitores = self._monitor_repo.listar_nomes()

        return {
            "rondas": rondas,
            "monitores": monitores,
            "filtro": filtro,
            "turnos": ["diurno", "noturno", "madrugada"],
            "status_opcoes": ["em_andamento", "finalizada", "com_alertas", "erro"],
        }

    # ── Envio ──────────────────────────────────────────────────────────────

    def enviar_relatorio(self, envio: EnvioEmail) -> tuple[bool, str]:
        """
        Compila o e-mail com as rondas selecionadas e envia via SMTP.
        Retorna (sucesso, mensagem).

        Fluxo:
          1. Busca os objetos Ronda pelos IDs selecionados
          2. Renderiza o template HTML do e-mail
          3. Monta a mensagem MIME (texto + imagens inline opcionais)
          4. Envia via SMTP com TLS
        """
        rondas = [
            self._ronda_repo.buscar_por_id(rid)
            for rid in envio.ronda_ids
        ]
        rondas = [r for r in rondas if r is not None]

        if not rondas:
            return False, "Nenhuma ronda válida selecionada."

        html_body = self._renderizar_template(rondas, envio.assunto)
        mensagem = self._montar_mime(envio, html_body, rondas)

        try:
            self._enviar_smtp(envio.destinatario, mensagem)
            return True, f"E-mail enviado para {envio.destinatario}."
        except smtplib.SMTPAuthenticationError:
            return False, "Falha de autenticação SMTP. Verifique usuário e senha."
        except smtplib.SMTPConnectError:
            return False, "Não foi possível conectar ao servidor SMTP."
        except Exception as exc:
            return False, f"Erro ao enviar e-mail: {exc}"

    # ── Internos ───────────────────────────────────────────────────────────

    def _renderizar_template(self, rondas: list, assunto: str) -> str:
        """
        Renderiza o template Jinja2 do corpo do e-mail.
        O template espera: rondas, assunto, gerado_em.

        Se o template não existir (ambiente de teste, por exemplo),
        gera um HTML mínimo como fallback.
        """
        try:
            return render_template(
                "email/relatorio_ronda.html",
                rondas=rondas,
                assunto=assunto,
                gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"),
            )
        except Exception:
            # Fallback para ambientes sem o template
            linhas = [
                f"<h2>{assunto}</h2>",
                f"<p>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>",
                "<ul>",
                *[
                    f"<li>Ronda #{r.id} — {r.monitor_nome} — {r.turno} — {r.status}</li>"
                    for r in rondas
                ],
                "</ul>",
            ]
            return "\n".join(linhas)

    def _montar_mime(
        self,
        envio: EnvioEmail,
        html_body: str,
        rondas: list,
    ) -> MIMEMultipart:
        """
        Constrói a mensagem MIME multipart/related.
        Imagens inline são referenciadas no HTML como cid:<nome_arquivo>.
        """
        cfg = current_app.config
        remetente = cfg.get("MAIL_SENDER", cfg.get("MAIL_USERNAME", ""))

        msg = MIMEMultipart("related")
        msg["Subject"] = envio.assunto
        msg["From"] = remetente
        msg["To"] = envio.destinatario

        # Parte alternativa: texto puro + HTML
        alternativo = MIMEMultipart("alternative")
        texto_puro = self._html_para_texto(html_body)
        alternativo.attach(MIMEText(texto_puro, "plain", "utf-8"))
        alternativo.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alternativo)

        if envio.incluir_imagens:
            self._anexar_imagens(msg, rondas)

        return msg

    @staticmethod
    def _anexar_imagens(msg: MIMEMultipart, rondas: list) -> None:
        """
        Anexa as imagens de alerta de cada ronda como partes inline.
        Usa o campo imagem_path dos alertas associados.
        Silencia erros de arquivo não encontrado para não interromper o envio.
        """
        for ronda in rondas:
            if not hasattr(ronda, "alertas"):
                continue
            for alerta in ronda.alertas:
                if not alerta.imagem_path:
                    continue
                caminho = Path(alerta.imagem_path)
                if not caminho.exists():
                    continue
                try:
                    with caminho.open("rb") as f:
                        img = MIMEImage(f.read())
                    img.add_header("Content-ID", f"<{caminho.name}>")
                    img.add_header(
                        "Content-Disposition", "inline", filename=caminho.name
                    )
                    msg.attach(img)
                except Exception:
                    continue

    def _enviar_smtp(self, destinatario: str, mensagem: MIMEMultipart) -> None:
        """
        Realiza a conexão SMTP e envia a mensagem.
        Suporta TLS (STARTTLS na porta 587) e SSL direto (porta 465).
        """
        cfg = current_app.config
        server = cfg.get("MAIL_SERVER", "localhost")
        port = int(cfg.get("MAIL_PORT", 587))
        use_tls = cfg.get("MAIL_USE_TLS", True)
        use_ssl = cfg.get("MAIL_USE_SSL", False)
        username = cfg.get("MAIL_USERNAME")
        password = cfg.get("MAIL_PASSWORD")
        remetente = cfg.get("MAIL_SENDER", username or "")

        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, context=context) as smtp:
                if username and password:
                    smtp.login(username, password)
                smtp.sendmail(remetente, destinatario, mensagem.as_string())
        else:
            with smtplib.SMTP(server, port) as smtp:
                if use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                if username and password:
                    smtp.login(username, password)
                smtp.sendmail(remetente, destinatario, mensagem.as_string())

    @staticmethod
    def _html_para_texto(html: str) -> str:
        """
        Remove tags HTML para gerar uma versão texto puro do e-mail.
        Solução simples sem dependências externas.
        """
        import re
        sem_tags = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s{2,}", "\n", sem_tags).strip()

"""
services/isapi_poller.py — Grupo Ronda · Conferência de Câmeras
Coleta status de NVRs e câmeras via Hikvision ISAPI.
 
Endpoints utilizados (autenticação HTTP Digest — RFC 2617):
  GET /ISAPI/System/workingstatus?format=json          → status geral (CPU, HD, canais)
  GET /ISAPI/System/workingstatus/chanStatus?format=json → status individual de cada canal
  GET /ISAPI/ContentMgmt/InputProxy/channels/status   → câmeras IP conectadas ao NVR
  GET /ISAPI/System/deviceInfo?format=json             → modelo, firmware, nº série
 
Logging:
  Cada polling gera entradas em duas saídas simultâneas:
    1. Logger Python padrão  → arquivo de log do Flask (via app.py)
    2. PollLog (in-memory)   → ring buffer por nvr_id, acessível via /conferencia/api/logs
"""
 
from __future__ import annotations
 
import concurrent.futures
import logging
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Optional
 
import requests
from requests.auth import HTTPDigestAuth
 
# ──────────────────────────────────────────────────────────────────────────────
# Logger do módulo — integra automaticamente com o logging do Flask
# ──────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
 
ISAPI_NS = "http://www.isapi.org/ver20/XMLSchema"
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Ring buffer de logs in-memory
# ──────────────────────────────────────────────────────────────────────────────
 
class PollLog:
    """
    Buffer circular de eventos de polling por nvr_id.
    Thread-safe. Mantém os últimos `maxlen` eventos globais
    e os últimos `per_nvr` eventos por NVR.
 
    Acessado pela rota GET /conferencia/api/logs para exibição em tempo real.
    """
 
    _global: deque = deque(maxlen=500)
    _per_nvr: dict[str, deque] = {}
    _lock: Lock = Lock()
 
    @classmethod
    def record(
        cls,
        nvr_id: str,
        level: str,       # "INFO" | "WARNING" | "ERROR" | "DEBUG"
        message: str,
        detail: str = "",
    ) -> None:
        entry = {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "nvr_id": nvr_id,
            "level": level,
            "message": message,
            "detail": detail,
        }
        with cls._lock:
            cls._global.append(entry)
            if nvr_id not in cls._per_nvr:
                cls._per_nvr[nvr_id] = deque(maxlen=100)
            cls._per_nvr[nvr_id].append(entry)
 
        # Espelha no logger Python para que o arquivo de log do Flask capture também
        log_fn = {
            "INFO":    logger.info,
            "WARNING": logger.warning,
            "ERROR":   logger.error,
            "DEBUG":   logger.debug,
        }.get(level, logger.info)
        msg = f"[{nvr_id}] {message}"
        if detail:
            msg += f" | {detail}"
        log_fn(msg)
 
    @classmethod
    def get_global(cls, limit: int = 200) -> list[dict]:
        with cls._lock:
            entries = list(cls._global)
        return entries[-limit:]
 
    @classmethod
    def get_nvr(cls, nvr_id: str, limit: int = 100) -> list[dict]:
        with cls._lock:
            buf = cls._per_nvr.get(nvr_id, deque())
            return list(buf)[-limit:]
 
    @classmethod
    def clear(cls, nvr_id: str | None = None) -> None:
        with cls._lock:
            if nvr_id:
                cls._per_nvr.pop(nvr_id, None)
            else:
                cls._global.clear()
                cls._per_nvr.clear()
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Modelos de dados
# ──────────────────────────────────────────────────────────────────────────────
 
@dataclass
class CameraStatus:
    channel_id: int
    channel_name: str = ""
    online: bool = False
    signal_ok: bool = False       # True = sinal normal (0 no ISAPI = normal)
    recording: bool = False
    record_status: int = 0        # 0=ok 1=exc HD 2=câmera offline 3=outro
    bit_rate_kbps: int = 0
    ip_address: str = ""
    model: str = ""
    raw_status: str = ""          # "online" | "offline" | "idle"
 
 
@dataclass
class HddStatus:
    hdd_id: int
    status: int = 0               # 0=ativo 1=sleep 2=exceção 4=não-formatado 5=desconectado
    capacity_mb: int = 0
    free_space_mb: int = 0
    enabled: bool = True
 
    @property
    def status_label(self) -> str:
        return {
            0: "Ativo", 1: "Dormindo", 2: "Exceção",
            3: "Erro (sleep)", 4: "Não formatado",
            5: "Desconectado", 6: "Formatando",
        }.get(self.status, "Desconhecido")
 
    @property
    def usage_pct(self) -> float:
        if self.capacity_mb <= 0:
            return 0.0
        return round((self.capacity_mb - self.free_space_mb) / self.capacity_mb * 100, 1)
 
 
@dataclass
class DeviceInfo:
    """Informações estáticas do dispositivo — capturadas uma vez e cacheadas."""
    model: str = ""
    firmware: str = ""
    serial: str = ""
    device_name: str = ""
 
 
@dataclass
class NvrStatus:
    nvr_id: str
    name: str
    host: str
    port: int
    reachable: bool = False
    error: str = ""
    dev_status: int = 0           # 0=normal 1=CPU alta 2=erro hardware
    cameras: list[CameraStatus] = field(default_factory=list)
    hdds: list[HddStatus] = field(default_factory=list)
    device_info: DeviceInfo = field(default_factory=DeviceInfo)
    polled_at: Optional[datetime] = None
    # Métricas de duração do polling (ms) para diagnóstico
    poll_duration_ms: int = 0
 
    @property
    def cameras_online(self) -> int:
        return sum(1 for c in self.cameras if c.online)
 
    @property
    def cameras_total(self) -> int:
        return len(self.cameras)
 
    @property
    def cameras_offline(self) -> int:
        return self.cameras_total - self.cameras_online
 
    @property
    def health_label(self) -> str:
        if not self.reachable:
            return "INACESSÍVEL"
        if self.cameras_offline > 0 or self.dev_status != 0:
            return "ATENÇÃO"
        return "OK"
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Cliente ISAPI
# ──────────────────────────────────────────────────────────────────────────────
 
class ISAPIClient:
    """
    Wrapper HTTP com HTTP Digest Auth (RFC 2617) para ISAPI Hikvision.
    Cada instância mantém uma Session para reaproveitar o handshake de autenticação.
    """
 
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: int = 8,
        use_https: bool = False,
    ):
        scheme = "https" if use_https else "http"
        self.base_url = f"{scheme}://{host}:{port}"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = HTTPDigestAuth(username, password)
        self.session.verify = False   # câmeras Hikvision usam cert auto-assinado
        if use_https:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
    def _get(self, path: str, accept_json: bool = False) -> requests.Response:
        url = self.base_url + path
        headers = {"Accept": "application/json"} if accept_json else {}
        resp = self.session.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp
 
    def get_json(self, path: str) -> dict:
        return self._get(path, accept_json=True).json()
 
    def get_xml(self, path: str) -> ET.Element:
        resp = self._get(path, accept_json=False)
        return ET.fromstring(resp.content)
 
    # ── Endpoints ISAPI ───────────────────────────────────────────────────
 
    def get_working_status(self) -> dict:
        """GET /ISAPI/System/workingstatus — status geral (CPU, HD, canais)."""
        return self.get_json("/ISAPI/System/workingstatus?format=json")
 
    def get_chan_status(self) -> dict:
        """GET /ISAPI/System/workingstatus/chanStatus — status por canal."""
        return self.get_json("/ISAPI/System/workingstatus/chanStatus?format=json")
 
    def get_inputproxy_status(self) -> ET.Element:
        """GET /ISAPI/ContentMgmt/InputProxy/channels/status — câmeras IP conectadas."""
        return self.get_xml("/ISAPI/ContentMgmt/InputProxy/channels/status")
 
    def get_device_info(self) -> dict:
        """GET /ISAPI/System/deviceInfo — modelo, firmware, nº série."""
        return self.get_json("/ISAPI/System/deviceInfo?format=json")
 
    def ping(self) -> bool:
        """Verifica alcançabilidade do dispositivo sem autenticação completa."""
        try:
            r = self.session.get(
                f"{self.base_url}/ISAPI/System/deviceInfo",
                timeout=self.timeout,
            )
            return r.status_code in (200, 401)  # 401 = NVR responde mas pede auth
        except Exception:
            return False
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Parsers de respostas ISAPI
# ──────────────────────────────────────────────────────────────────────────────
 
def _ns(tag: str) -> str:
    return f"{{{ISAPI_NS}}}{tag}"
 
 
def parse_chan_status(data: dict) -> list[CameraStatus]:
    """
    Parseia JSON_ChanStatus.
    DS-7732NI-I4(B) retorna: {"ChanStatusList": {"ChanStatus": [...]}}
    Alguns modelos retornam:  {"ChanStatus": [...]}
    bitRate vem em bits/s — convertido para Kbps dividindo por 1024.
    O nome da câmera já vem no campo "name" desta resposta.
    """
    cameras: list[CameraStatus] = []
 
    # Normaliza wrapper ChanStatusList (DS-7732 e similares)
    if "ChanStatusList" in data:
        chan_list = data["ChanStatusList"].get("ChanStatus", [])
    else:
        chan_list = data.get("ChanStatus", [])
 
    if isinstance(chan_list, dict):
        chan_list = [chan_list]
 
    for ch in chan_list:
        bit_rate_raw = int(ch.get("bitRate", 0))
        # bitRate pode vir em bits/s (>100000) ou já em Kbps (<100000)
        bit_rate_kbps = bit_rate_raw // 1024 if bit_rate_raw > 100_000 else bit_rate_raw
 
        cameras.append(CameraStatus(
            channel_id=int(ch.get("chanNo", 0)),
            channel_name=ch.get("name", ""),   # DS-7732 inclui nome aqui
            online=int(ch.get("online", 0)) == 1,
            signal_ok=int(ch.get("signal", 1)) == 0,   # 0=normal 1=perda de sinal
            recording=int(ch.get("record", 0)) == 1,
            record_status=int(ch.get("recordStatus", 0)),
            bit_rate_kbps=bit_rate_kbps,
        ))
    return cameras
 
 
def parse_hd_status(data: dict) -> list[HddStatus]:
    """Parseia HDStatus dentro de JSON_WorkingStatus."""
    ws = data.get("WorkingStatus", data)
    hd_list = ws.get("HDStatus", [])
    if isinstance(hd_list, dict):
        hd_list = [hd_list]
    return [
        HddStatus(
            hdd_id=int(hd.get("hdNo", 0)),
            status=int(hd.get("status", 0)),
            capacity_mb=int(hd.get("volume", 0)),
            free_space_mb=int(hd.get("freeSpace", 0)),
            enabled=hd.get("enable", 1) != 0,
        )
        for hd in hd_list
    ]
 
 
def parse_inputproxy_status(root: ET.Element) -> dict[int, dict]:
    """
    Parseia XML_InputProxyChannelStatusList ou XML_InputProxyChannelList.
    Suporta ambos os endpoints:
      /InputProxy/channels/status  → online/ip (sem nome/modelo)
      /InputProxy/channels         → nome/ip/modelo (sem status online)
    Retorna {channelID: {ip, name, model, raw_status}}.
    """
    result: dict[int, dict] = {}
 
    # Tenta InputProxyChannelStatus (endpoint /status)
    for ch in root.iter(_ns("InputProxyChannelStatus")):
        ch_id_el = ch.find(_ns("id"))
        if ch_id_el is None:
            continue
        ch_id = int(ch_id_el.text or 0)
 
        ip = ""
        src = ch.find(_ns("sourceInputPortDescriptor"))
        if src is not None:
            ip_el = src.find(_ns("ipAddress"))
            if ip_el is not None:
                ip = ip_el.text or ""
 
        online_el = ch.find(_ns("online"))
        raw_status = "unknown"
        if online_el is not None:
            raw_status = "online" if online_el.text == "true" else "offline"
 
        result[ch_id] = {"ip": ip, "name": "", "model": "", "raw_status": raw_status}
 
    # Tenta InputProxyChannel (endpoint /channels) — tem nome e modelo
    for ch in root.iter(_ns("InputProxyChannel")):
        ch_id_el = ch.find(_ns("id"))
        if ch_id_el is None:
            continue
        ch_id = int(ch_id_el.text or 0)
 
        name = ""
        name_el = ch.find(_ns("name"))
        if name_el is not None:
            name = name_el.text or ""
 
        ip = ""
        model = ""
        src = ch.find(_ns("sourceInputPortDescriptor"))
        if src is not None:
            ip_el = src.find(_ns("ipAddress"))
            if ip_el is not None:
                ip = ip_el.text or ""
            model_el = src.find(_ns("model"))
            if model_el is not None:
                model = model_el.text or ""
 
        existing = result.get(ch_id, {})
        result[ch_id] = {
            "ip":         ip or existing.get("ip", ""),
            "name":       name or existing.get("name", ""),
            "model":      model or existing.get("model", ""),
            "raw_status": existing.get("raw_status", "unknown"),
        }
 
    return result
 
 
def parse_device_info(data: dict) -> DeviceInfo:
    """
    Parseia DeviceInfo.
    Alguns NVRs (ex: DS-7732NI-I4(B)) retornam XML mesmo com ?format=json.
    Neste caso o dict virá vazio e o XML já foi parseado pelo cliente.
    """
    di = data.get("DeviceInfo", data)
    return DeviceInfo(
        model=di.get("model", ""),
        firmware=di.get("firmwareVersion", ""),
        serial=di.get("serialNumber", ""),
        device_name=di.get("deviceName", ""),
    )
 
 
def parse_device_info_xml(root: ET.Element) -> DeviceInfo:
    """Parseia DeviceInfo quando o NVR retorna XML em vez de JSON."""
    def txt(tag: str) -> str:
        el = root.find(_ns(tag))
        return el.text.strip() if el is not None and el.text else ""
    return DeviceInfo(
        model=txt("model"),
        firmware=txt("firmwareVersion"),
        serial=txt("serialNumber"),
        device_name=txt("deviceName"),
    )
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Poller de um único NVR
# ──────────────────────────────────────────────────────────────────────────────
 
class CameraConferencePoller:
    """
    Faz polling completo de um NVR via ISAPI e retorna NvrStatus.
    Cada endpoint é tentado de forma independente — falha em um não
    interrompe os demais (tolerância a falha parcial).
 
    Todos os eventos são registrados em PollLog para exibição em tempo real.
    """
 
    def __init__(
        self,
        client: ISAPIClient,
        nvr_id: str,
        nvr_name: str,
        nvr_host: str,
        nvr_port: int,
    ):
        self.client = client
        self.nvr_id = nvr_id
        self.nvr_name = nvr_name
        self.nvr_host = nvr_host
        self.nvr_port = nvr_port
 
    def _log(self, level: str, message: str, detail: str = "") -> None:
        PollLog.record(self.nvr_id, level, message, detail)
 
    def poll(self) -> NvrStatus:
        t_start = datetime.now()
        self._log("INFO", f"Iniciando polling — {self.nvr_host}:{self.nvr_port}")
 
        result = NvrStatus(
            nvr_id=self.nvr_id,
            name=self.nvr_name,
            host=self.nvr_host,
            port=self.nvr_port,
            polled_at=t_start,
        )
 
        # ── 1. Verificação de alcançabilidade ─────────────────────────────
        if not self.client.ping():
            result.error = "Dispositivo inacessível (ping ISAPI falhou)"
            result.reachable = False
            self._log("ERROR", "Dispositivo inacessível", result.error)
            result.poll_duration_ms = int((datetime.now() - t_start).total_seconds() * 1000)
            return result
 
        self._log("DEBUG", "Ping OK — dispositivo responde")
 
        # ── 2. Informações do dispositivo ──────────────────────────────────
        try:
            # DS-7732NI-I4(B) retorna XML mesmo com ?format=json — tenta JSON, cai em XML
            try:
                dev_data = self.client.get_json("/ISAPI/System/deviceInfo?format=json")
                if "model" in str(dev_data):
                    result.device_info = parse_device_info(dev_data)
                else:
                    raise ValueError("Resposta não parece JSON de DeviceInfo")
            except Exception:
                dev_root = self.client.get_xml("/ISAPI/System/deviceInfo")
                result.device_info = parse_device_info_xml(dev_root)
            self._log(
                "INFO",
                "DeviceInfo obtido",
                f"modelo={result.device_info.model} firmware={result.device_info.firmware}",
            )
        except Exception as e:
            self._log("WARNING", "DeviceInfo falhou (não crítico)", str(e))
 
        # ── 3. Status de canais (câmeras) ──────────────────────────────────
        try:
            chan_data = self.client.get_chan_status()
            result.cameras = parse_chan_status(chan_data)
            result.reachable = True
            online = sum(1 for c in result.cameras if c.online)
            total = len(result.cameras)
            self._log(
                "INFO" if online == total else "WARNING",
                f"Canais: {online}/{total} online",
                f"{total - online} offline" if online < total else "",
            )
            # Log individual de câmeras offline
            for cam in result.cameras:
                if not cam.online:
                    self._log(
                        "WARNING",
                        f"Canal {cam.channel_id} OFFLINE",
                        f"record_status={cam.record_status}",
                    )
        except Exception as e:
            result.error = str(e)
            self._log("ERROR", "chanStatus falhou", str(e))
 
        # ── 4. Status geral do dispositivo (CPU + HD) ─────────────────────
        try:
            ws_data = self.client.get_working_status()
            ws = ws_data.get("WorkingStatus", ws_data)
            result.dev_status = int(ws.get("devStatus", 0))
            result.hdds = parse_hd_status(ws_data)
            result.reachable = True
 
            # Log de status do dispositivo
            dev_label = {0: "Normal", 1: "CPU alta", 2: "Erro hardware"}.get(
                result.dev_status, f"status={result.dev_status}"
            )
            self._log(
                "INFO" if result.dev_status == 0 else "WARNING",
                f"Dispositivo: {dev_label}",
            )
 
            # Log de HDs
            for hd in result.hdds:
                level = "INFO" if hd.status == 0 else "WARNING"
                self._log(
                    level,
                    f"HD {hd.hdd_id}: {hd.status_label} — uso {hd.usage_pct}%",
                    f"livre={hd.free_space_mb}MB de {hd.capacity_mb}MB",
                )
        except Exception as e:
            self._log("WARNING", "workingstatus falhou", str(e))
 
        # ── 5. Enriquecimento via InputProxy (IP, nome e modelo) ──────────
        try:
            # /status → online/ip
            proxy_info: dict[int, dict] = {}
            try:
                status_root = self.client.get_inputproxy_status()
                proxy_info = parse_inputproxy_status(status_root)
            except Exception as e:
                self._log("DEBUG", "InputProxy/status falhou", str(e))
 
            # /channels → nome + modelo (endpoint separado no DS-7732)
            try:
                chan_root = self.client.get_xml("/ISAPI/ContentMgmt/InputProxy/channels")
                channels_info = parse_inputproxy_status(chan_root)
                # Mescla: channels tem nome/modelo, status tem online/ip
                for ch_id, ch_data in channels_info.items():
                    existing = proxy_info.get(ch_id, {})
                    proxy_info[ch_id] = {
                        "ip":         ch_data.get("ip") or existing.get("ip", ""),
                        "name":       ch_data.get("name") or existing.get("name", ""),
                        "model":      ch_data.get("model") or existing.get("model", ""),
                        "raw_status": existing.get("raw_status", "unknown"),
                    }
            except Exception as e:
                self._log("DEBUG", "InputProxy/channels falhou", str(e))
 
            enriched = 0
            for cam in result.cameras:
                info = proxy_info.get(cam.channel_id, {})
                if info.get("name") and not cam.channel_name:
                    cam.channel_name = info["name"]
                if info.get("ip"):
                    cam.ip_address = info["ip"]
                if info.get("model"):
                    cam.model = info["model"]
                if info.get("raw_status") and info["raw_status"] != "unknown":
                    cam.raw_status = info["raw_status"]
                if info:
                    enriched += 1
            self._log("DEBUG", f"InputProxy: {enriched} câmeras enriquecidas com IP/nome/modelo")
        except Exception as e:
            self._log("DEBUG", "InputProxy enrich falhou (não crítico)", str(e))
 
        # ── Finalização ───────────────────────────────────────────────────
        duration_ms = int((datetime.now() - t_start).total_seconds() * 1000)
        result.poll_duration_ms = duration_ms
 
        health = result.health_label
        level = "INFO" if health == "OK" else ("WARNING" if health == "ATENÇÃO" else "ERROR")
        self._log(
            level,
            f"Polling concluído — health={health} ({duration_ms}ms)",
            f"câmeras={result.cameras_online}/{result.cameras_total} online",
        )
 
        return result
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Gerenciador multi-NVR
# ──────────────────────────────────────────────────────────────────────────────
 
@dataclass
class NvrConfig:
    nvr_id: str
    name: str
    host: str
    port: int
    username: str
    password: str
    use_https: bool = False
 
 
class ConferenceManager:
    """
    Coordena polling paralelo de múltiplos NVRs via ThreadPoolExecutor.
    Falha em um NVR não afeta os demais.
    """
 
    def __init__(
        self,
        nvr_configs: list[NvrConfig],
        workers: int = 4,
        timeout: int = 8,
    ):
        self.nvr_configs = nvr_configs
        self.workers = workers
        self.timeout = timeout
 
    def _poll_one(self, cfg: NvrConfig) -> NvrStatus:
        client = ISAPIClient(
            cfg.host, cfg.port, cfg.username, cfg.password,
            timeout=self.timeout, use_https=cfg.use_https,
        )
        poller = CameraConferencePoller(
            client, cfg.nvr_id, cfg.name, cfg.host, cfg.port,
        )
        try:
            return poller.poll()
        except Exception as e:
            PollLog.record(cfg.nvr_id, "ERROR", "Polling falhou completamente", str(e))
            logger.exception(f"[{cfg.nvr_id}] Polling falhou completamente")
            return NvrStatus(
                nvr_id=cfg.nvr_id,
                name=cfg.name,
                host=cfg.host,
                port=cfg.port,
                reachable=False,
                error=str(e),
                polled_at=datetime.now(),
            )
 
    def poll_all(self) -> list[NvrStatus]:
        """
        Executa polling de todos os NVRs em paralelo.
        Retorna lista ordenada conforme a ordem original de nvr_configs.
        """
        if not self.nvr_configs:
            logger.warning("ConferenceManager.poll_all: nenhum NVR configurado")
            return []
 
        logger.info(f"ConferenceManager: iniciando polling de {len(self.nvr_configs)} NVR(s)")
 
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self._poll_one, cfg): cfg for cfg in self.nvr_configs}
            results: list[NvrStatus] = []
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
 
        order = {cfg.nvr_id: i for i, cfg in enumerate(self.nvr_configs)}
        results.sort(key=lambda r: order.get(r.nvr_id, 999))
 
        ok = sum(1 for r in results if r.health_label == "OK")
        logger.info(
            f"ConferenceManager: polling concluído — "
            f"{ok}/{len(results)} NVRs OK"
        )
        return results

        """
services/monitor_engine_service.py — Motor de avaliação estilo "Triggers" do Zabbix.

Recebe o resultado de um polling (NvrStatus, com suas CameraStatus) e decide:
  - Quais condições de problema estão ativas agora (NVR inacessível,
    NVR em atenção, câmera offline, câmera sem sinal)
  - Abre um MonitorEvent quando uma condição passa a existir
  - Fecha (resolve) o MonitorEvent quando a condição deixa de existir
  - Sinaliza quais eventos são "novos" (para quem chamar disparar notificação)

Mantém o estado de "o que já está aberto" consultando o próprio banco,
então funciona corretamente mesmo se o processo for reiniciado.
"""

from __future__ import annotations

from datetime import datetime

from extensions import db
from models.monitoring import CameraStatusLog, MonitorEvent
from models.nvr_status_log import NvrStatusLog
from services.isapi_poller import NvrStatus

# Severidade por tipo de problema — ajuste livremente conforme sua operação.
SEVERIDADE = {
    "nvr_inacessivel": "critica",
    "nvr_atencao": "media",
    "camera_offline": "alta",
    "camera_sem_sinal": "media",
}


class MonitorEngineService:
    """Avalia um ciclo de polling e mantém o estado de eventos no banco."""

    def processar(self, resultados: list[NvrStatus]) -> list[MonitorEvent]:
        """
        Processa uma lista de NvrStatus (resultado de ConferenceManager.poll_all).
        Grava histórico (NVR + câmeras) e atualiza eventos.
        Retorna a lista de eventos NOVOS abertos neste ciclo (para notificação).
        """
        novos_eventos: list[MonitorEvent] = []

        for nvr in resultados:
            self._gravar_historico_nvr(nvr)
            novos_eventos += self._avaliar_nvr(nvr)

            for cam in nvr.cameras:
                self._gravar_historico_camera(nvr.nvr_id, cam)
                novos_eventos += self._avaliar_camera(nvr, cam)

        db.session.commit()
        return novos_eventos

    # ── Histórico ────────────────────────────────────────────────────────────

    def _gravar_historico_nvr(self, nvr: NvrStatus) -> None:
        db.session.add(NvrStatusLog(
            nvr_id=nvr.nvr_id,
            nvr_nome=nvr.name,
            timestamp=nvr.polled_at or datetime.utcnow(),
            health=nvr.health_label,
            reachable=nvr.reachable,
            cameras_total=nvr.cameras_total,
            cameras_online=nvr.cameras_online,
            cameras_offline=nvr.cameras_offline,
            erro=nvr.error or None,
        ))

    def _gravar_historico_camera(self, nvr_id: str, cam) -> None:
        db.session.add(CameraStatusLog(
            nvr_id=nvr_id,
            channel_id=cam.channel_id,
            channel_name=cam.channel_name or f"Canal {cam.channel_id}",
            online=cam.online,
            signal_ok=cam.signal_ok,
            recording=cam.recording,
            bit_rate_kbps=cam.bit_rate_kbps,
        ))

    # ── Avaliação NVR ────────────────────────────────────────────────────────

    def _avaliar_nvr(self, nvr: NvrStatus) -> list[MonitorEvent]:
        novos = []

        if not nvr.reachable:
            novos += self._abrir_se_necessario(
                alvo_tipo="nvr", nvr_id=nvr.nvr_id, channel_id=None,
                chave="nvr_inacessivel", nome=nvr.name,
                mensagem=f"NVR '{nvr.name}' inacessível. {nvr.error or ''}".strip(),
            )
            # Se está inacessível, não faz sentido também ter "atenção" aberto por baixo
            self._resolver_se_aberto(nvr.nvr_id, None, "nvr_atencao")
        else:
            self._resolver_se_aberto(nvr.nvr_id, None, "nvr_inacessivel")

            if nvr.cameras_offline > 0 or nvr.dev_status != 0:
                novos += self._abrir_se_necessario(
                    alvo_tipo="nvr", nvr_id=nvr.nvr_id, channel_id=None,
                    chave="nvr_atencao", nome=nvr.name,
                    mensagem=(
                        f"NVR '{nvr.name}' em atenção: "
                        f"{nvr.cameras_offline} câmera(s) offline, dev_status={nvr.dev_status}."
                    ),
                )
            else:
                self._resolver_se_aberto(nvr.nvr_id, None, "nvr_atencao")

        return novos

    # ── Avaliação Câmera ─────────────────────────────────────────────────────

    def _avaliar_camera(self, nvr: NvrStatus, cam) -> list[MonitorEvent]:
        novos = []
        nome_cam = f"{nvr.name} / {cam.channel_name or f'Canal {cam.channel_id}'}"

        # Se o NVR está inacessível, não cravamos problema de câmera
        # individual (seria ruído: não sabemos o estado real dela).
        if not nvr.reachable:
            return novos

        if not cam.online:
            novos += self._abrir_se_necessario(
                alvo_tipo="camera", nvr_id=nvr.nvr_id, channel_id=cam.channel_id,
                chave="camera_offline", nome=nome_cam,
                mensagem=f"Câmera '{nome_cam}' está offline.",
            )
        else:
            self._resolver_se_aberto(nvr.nvr_id, cam.channel_id, "camera_offline")

            if not cam.signal_ok:
                novos += self._abrir_se_necessario(
                    alvo_tipo="camera", nvr_id=nvr.nvr_id, channel_id=cam.channel_id,
                    chave="camera_sem_sinal", nome=nome_cam,
                    mensagem=f"Câmera '{nome_cam}' está online porém sem sinal de vídeo.",
                )
            else:
                self._resolver_se_aberto(nvr.nvr_id, cam.channel_id, "camera_sem_sinal")

        return novos

    # ── Internos: abrir/resolver evento (idempotente) ───────────────────────

    def _abrir_se_necessario(
        self, alvo_tipo: str, nvr_id: str, channel_id: int | None,
        chave: str, nome: str, mensagem: str,
    ) -> list[MonitorEvent]:
        existente = self._buscar_evento_aberto(nvr_id, channel_id, chave)
        if existente:
            return []  # já está aberto, não duplica

        evento = MonitorEvent(
            alvo_tipo=alvo_tipo,
            nvr_id=nvr_id,
            channel_id=channel_id,
            nome_exibicao=nome,
            severidade=SEVERIDADE.get(chave, "media"),
            chave_problema=chave,
            mensagem=mensagem,
        )
        db.session.add(evento)
        db.session.flush()  # garante evento.id antes de retornar
        return [evento]

    def _resolver_se_aberto(self, nvr_id: str, channel_id: int | None, chave: str) -> None:
        existente = self._buscar_evento_aberto(nvr_id, channel_id, chave)
        if existente:
            existente.resolvido_em = datetime.utcnow()

    def _buscar_evento_aberto(
        self, nvr_id: str, channel_id: int | None, chave: str,
    ) -> MonitorEvent | None:
        query = MonitorEvent.query.filter_by(
            nvr_id=nvr_id, chave_problema=chave, resolvido_em=None,
        )
        if channel_id is None:
            query = query.filter(MonitorEvent.channel_id.is_(None))
        else:
            query = query.filter_by(channel_id=channel_id)
        return query.first()

"""
services/monitor_notification_service.py — Notificações de eventos de monitoramento.

Desacoplado do MonitorEngineService para facilitar adicionar outros canais
no futuro (WhatsApp, Telegram, webhook) sem tocar na lógica de triggers.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app

from models.monitoring import MonitorEvent

logger = logging.getLogger(__name__)

EMOJI_SEVERIDADE = {
    "critica": "🔴",
    "alta": "🟠",
    "media": "🟡",
    "baixa": "🔵",
}


class MonitorNotificationService:
    def notificar_novos_eventos(self, eventos: list[MonitorEvent]) -> None:
        for evento in eventos:
            self._enviar_email(evento)

    def notificar_resolucao(self, evento: MonitorEvent) -> None:
        self._enviar_email(evento, resolucao=True)

    # ── Internos ─────────────────────────────────────────────────────────────

    def _enviar_email(self, evento: MonitorEvent, resolucao: bool = False) -> None:
        destinatario = current_app.config.get("MAIL_DEFAULT_RECEIVER")
        if not destinatario:
            logger.warning("MAIL_DEFAULT_RECEIVER não configurado — alerta não enviado.")
            return

        emoji = "✅" if resolucao else EMOJI_SEVERIDADE.get(evento.severidade, "⚪")
        titulo = "RESOLVIDO" if resolucao else "PROBLEMA"
        assunto = f"{emoji} [{titulo}] {evento.nome_exibicao} — {evento.chave_problema}"

        corpo = (
            f"Alvo: {evento.nome_exibicao} ({evento.alvo_tipo})\n"
            f"Problema: {evento.chave_problema}\n"
            f"Severidade: {evento.severidade}\n"
            f"Mensagem: {evento.mensagem}\n"
            f"Aberto em: {evento.aberto_em.strftime('%d/%m/%Y %H:%M:%S')}\n"
        )
        if resolucao:
            corpo += (
                f"Resolvido em: {evento.resolvido_em.strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"Duração: {evento.duracao_minutos} min\n"
            )

        try:
            self._enviar_smtp(destinatario, assunto, corpo)
            evento.notificado = True
            logger.info(f"Notificação enviada: {assunto}")
        except Exception:
            logger.exception(f"Falha ao enviar notificação do evento #{evento.id}")

    @staticmethod
    def _enviar_smtp(destinatario: str, assunto: str, corpo_texto: str) -> None:
        cfg = current_app.config
        server = cfg.get("MAIL_SERVER", "localhost")
        port = int(cfg.get("MAIL_PORT", 587))
        use_tls = cfg.get("MAIL_USE_TLS", True)
        use_ssl = cfg.get("MAIL_USE_SSL", False)
        username = cfg.get("MAIL_USERNAME")
        password = cfg.get("MAIL_PASSWORD")
        remetente = cfg.get("MAIL_SENDER", username or "")

        msg = MIMEMultipart()
        msg["Subject"] = assunto
        msg["From"] = remetente
        msg["To"] = destinatario
        msg.attach(MIMEText(corpo_texto, "plain", "utf-8"))

        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, context=context) as smtp:
                if username and password:
                    smtp.login(username, password)
                smtp.sendmail(remetente, destinatario, msg.as_string())
        else:
            with smtplib.SMTP(server, port) as smtp:
                if use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                if username and password:
                    smtp.login(username, password)
                smtp.sendmail(remetente, destinatario, msg.as_string())

"""
services/relatorio_conferencia.py — Grupo Ronda · Gerador de Relatório Técnico

Gera relatório de monitoramento de NVRs e câmeras em PDF ou Excel.
Baseado nos modelos: NvrStatusLog, CameraStatusLog, MonitorEvent.

Uso:
    from services.relatorio_conferencia import gerar_relatorio
    pdf_bytes = gerar_relatorio(dt_inicio, dt_fim, fmt="pdf")
    xlsx_bytes = gerar_relatorio(dt_inicio, dt_fim, fmt="xlsx")
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from typing import Literal

# ── ReportLab ────────────────────────────────────────────────────────────────
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

# ── OpenPyXL ─────────────────────────────────────────────────────────────────
import openpyxl
from openpyxl.styles import (
    Alignment, Border, Font, PatternFill, Side,
)
from openpyxl.utils import get_column_letter


# ──────────────────────────────────────────────────────────────────────────────
# Cores Grupo Ronda
# ──────────────────────────────────────────────────────────────────────────────
GOLD   = colors.HexColor("#F5C400")
BLACK  = colors.HexColor("#0A0A0A")
DARK   = colors.HexColor("#1A1A1A")
GRAY   = colors.HexColor("#4A4A4A")
LGRAY  = colors.HexColor("#E8E8E8")
GREEN  = colors.HexColor("#22C55E")
RED    = colors.HexColor("#EF4444")
ORANGE = colors.HexColor("#F59E0B")
WHITE  = colors.white

GOLD_HEX   = "F5C400"
BLACK_HEX  = "0A0A0A"
RED_HEX    = "EF4444"
GREEN_HEX  = "22C55E"
ORANGE_HEX = "F59E0B"
LGRAY_HEX  = "F3F3F3"
DGRAY_HEX  = "4A4A4A"


# ──────────────────────────────────────────────────────────────────────────────
# Estilos ReportLab
# ──────────────────────────────────────────────────────────────────────────────

def _estilos():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "rg_title", fontSize=16, fontName="Helvetica-Bold",
            textColor=BLACK, alignment=TA_CENTER, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "rg_subtitle", fontSize=10, fontName="Helvetica",
            textColor=GRAY, alignment=TA_CENTER, spaceAfter=2,
        ),
        "section": ParagraphStyle(
            "rg_section", fontSize=9, fontName="Helvetica-Bold",
            textColor=BLACK, spaceBefore=8, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "rg_body", fontSize=8, fontName="Helvetica",
            textColor=GRAY, spaceAfter=3, leading=12,
        ),
        "label": ParagraphStyle(
            "rg_label", fontSize=7, fontName="Helvetica-Bold",
            textColor=GRAY, alignment=TA_CENTER,
        ),
        "value": ParagraphStyle(
            "rg_value", fontSize=9, fontName="Helvetica-Bold",
            textColor=BLACK, alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "rg_footer", fontSize=7, fontName="Helvetica",
            textColor=GRAY, alignment=TA_CENTER,
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Consultas ao banco
# ──────────────────────────────────────────────────────────────────────────────

def _buscar_dados(dt_inicio: datetime, dt_fim: datetime) -> dict:
    from models.monitoring import CameraStatusLog, MonitorEvent
    from models.nvr_status_log import NvrStatusLog

    # Logs de NVR no período
    nvr_logs = (
        NvrStatusLog.query
        .filter(NvrStatusLog.timestamp >= dt_inicio,
                NvrStatusLog.timestamp <= dt_fim)
        .order_by(NvrStatusLog.nvr_id, NvrStatusLog.timestamp)
        .all()
    )

    # Logs de câmera no período
    cam_logs = (
        CameraStatusLog.query
        .filter(CameraStatusLog.timestamp >= dt_inicio,
                CameraStatusLog.timestamp <= dt_fim)
        .order_by(CameraStatusLog.nvr_id,
                  CameraStatusLog.channel_id,
                  CameraStatusLog.timestamp)
        .all()
    )

    # Eventos que se sobrepõem ao período
    eventos = (
        MonitorEvent.query
        .filter(
            MonitorEvent.aberto_em <= dt_fim,
            (MonitorEvent.resolvido_em == None) |
            (MonitorEvent.resolvido_em >= dt_inicio),
        )
        .order_by(MonitorEvent.aberto_em)
        .all()
    )

    return {"nvr_logs": nvr_logs, "cam_logs": cam_logs, "eventos": eventos}


def _calcular_resumo(dados: dict, dt_inicio: datetime, dt_fim: datetime) -> dict:
    """Calcula métricas agregadas para o relatório."""
    nvr_logs = dados["nvr_logs"]
    cam_logs = dados["cam_logs"]
    eventos  = dados["eventos"]

    periodo_h = max((dt_fim - dt_inicio).total_seconds() / 3600, 0.01)

    # NVRs únicos
    nvrs = {}
    for log in nvr_logs:
        if log.nvr_id not in nvrs:
            nvrs[log.nvr_id] = {"nome": log.nvr_nome, "logs": []}
        nvrs[log.nvr_id]["logs"].append(log)

    # Uptime por NVR
    for nvr_id, info in nvrs.items():
        logs = info["logs"]
        total = len(logs)
        ok = sum(1 for l in logs if l.health == "OK")
        info["uptime_pct"] = round(ok / total * 100, 1) if total else 0
        info["total_polls"] = total
        info["polls_ok"] = ok

    # Câmeras únicas
    cameras = {}
    for log in cam_logs:
        key = (log.nvr_id, log.channel_id)
        if key not in cameras:
            cameras[key] = {"nome": log.channel_name, "nvr_id": log.nvr_id, "logs": []}
        cameras[key]["logs"].append(log)

    for key, info in cameras.items():
        logs = info["logs"]
        total = len(logs)
        online = sum(1 for l in logs if l.online)
        info["uptime_pct"] = round(online / total * 100, 1) if total else 0
        info["total_polls"] = total
        info["polls_online"] = online

    # Eventos por categoria
    nvr_eventos  = [e for e in eventos if e.alvo_tipo == "nvr"]
    cam_eventos  = [e for e in eventos if e.alvo_tipo == "camera"]
    ativos       = [e for e in eventos if e.resolvido_em is None]

    return {
        "nvrs": nvrs,
        "cameras": cameras,
        "nvr_eventos": nvr_eventos,
        "cam_eventos": cam_eventos,
        "ativos": ativos,
        "periodo_h": periodo_h,
        "total_eventos": len(eventos),
        "total_nvrs": len(nvrs),
        "total_cameras": len(cameras),
        "cameras_problema": sum(1 for info in cameras.values() if info["uptime_pct"] < 100),
    }


def _fmt_dur(minutos: float | None) -> str:
    if minutos is None:
        return "–"
    if minutos < 60:
        return f"{int(minutos)}min"
    h = int(minutos // 60)
    m = int(minutos % 60)
    return f"{h}h {m}min"


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "Em aberto"
    return dt.strftime("%d/%m/%Y %H:%M")


# ──────────────────────────────────────────────────────────────────────────────
# Gerador PDF
# ──────────────────────────────────────────────────────────────────────────────

def _gerar_pdf(dt_inicio: datetime, dt_fim: datetime, dados: dict, resumo: dict) -> bytes:
    buf = io.BytesIO()
    W, H = A4
    margin = 18 * mm

    estilos = _estilos()
    story = []

    # ── Cabeçalho (papel timbrado) ────────────────────────────────────────
    # Faixa dourada superior
    header_table = Table(
        [[
            Paragraph("<b>GRUPO<br/>RONDA</b>",
                      ParagraphStyle("logo", fontSize=14, fontName="Helvetica-Bold",
                                     textColor=BLACK, leading=16)),
            Paragraph(
                "RELATÓRIO TÉCNICO OPERACIONAL<br/>"
                "<font size=9>Monitoramento de NVRs e Câmeras</font>",
                ParagraphStyle("htitle", fontSize=12, fontName="Helvetica-Bold",
                               textColor=WHITE, alignment=TA_CENTER, leading=16)
            ),
            Paragraph(
                f"<font size=7>Emitido em<br/>{datetime.now().strftime('%d/%m/%Y %H:%M')}</font>",
                ParagraphStyle("hdate", fontSize=7, fontName="Helvetica",
                               textColor=WHITE, alignment=TA_RIGHT)
            ),
        ]],
        colWidths=[40*mm, W - 2*margin - 80*mm, 40*mm],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), GOLD),
        ("BACKGROUND", (1, 0), (2, 0), BLACK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4*mm))

    # ── Período ───────────────────────────────────────────────────────────
    story.append(Paragraph(
        f"Período: {dt_inicio.strftime('%d/%m/%Y %H:%M')} — {dt_fim.strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle("periodo", fontSize=9, fontName="Helvetica-Bold",
                       textColor=GRAY, alignment=TA_CENTER),
    ))
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD))
    story.append(Spacer(1, 4*mm))

    # ── Resumo executivo ──────────────────────────────────────────────────
    story.append(Paragraph("1. RESUMO EXECUTIVO", estilos["section"]))

    # Cards de métricas
    cards = [
        [
            Paragraph(str(resumo["total_nvrs"]), estilos["value"]),
            Paragraph(str(resumo["total_cameras"]), estilos["value"]),
            Paragraph(str(resumo["total_eventos"]), estilos["value"]),
            Paragraph(str(len(resumo["ativos"])), estilos["value"]),
            Paragraph(str(resumo["cameras_problema"]), estilos["value"]),
        ],
        [
            Paragraph("NVRs Monitorados", estilos["label"]),
            Paragraph("Câmeras Monitoradas", estilos["label"]),
            Paragraph("Total de Eventos", estilos["label"]),
            Paragraph("Eventos Ativos", estilos["label"]),
            Paragraph("Câmeras c/ Falha", estilos["label"]),
        ],
    ]
    cw = (W - 2*margin) / 5
    cards_table = Table(cards, colWidths=[cw]*5)
    cards_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LGRAY),
        ("BACKGROUND", (3, 0), (3, 0), RED if resumo["ativos"] else GREEN),
        ("BACKGROUND", (4, 0), (4, 0), ORANGE if resumo["cameras_problema"] else GREEN),
        ("TEXTCOLOR",  (3, 0), (3, 0), WHITE),
        ("TEXTCOLOR",  (4, 0), (4, 0), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.5, LGRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, LGRAY),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(cards_table)
    story.append(Spacer(1, 4*mm))

    # ── Status por NVR ────────────────────────────────────────────────────
    story.append(Paragraph("2. STATUS DOS NVRs", estilos["section"]))

    nvr_rows = [[
        Paragraph("NVR", estilos["label"]),
        Paragraph("Total Polls", estilos["label"]),
        Paragraph("Polls OK", estilos["label"]),
        Paragraph("Uptime %", estilos["label"]),
        Paragraph("Câmeras Online (último)", estilos["label"]),
    ]]
    for nvr_id, info in resumo["nvrs"].items():
        logs = info["logs"]
        ultimo = logs[-1] if logs else None
        uptime = info["uptime_pct"]
        cor = GREEN if uptime >= 99 else (ORANGE if uptime >= 90 else RED)
        nvr_rows.append([
            Paragraph(info["nome"], estilos["body"]),
            Paragraph(str(info["total_polls"]), estilos["body"]),
            Paragraph(str(info["polls_ok"]), estilos["body"]),
            Paragraph(
                f'<font color="#{("22C55E" if uptime>=99 else ("F59E0B" if uptime>=90 else "EF4444"))}">'
                f'<b>{uptime}%</b></font>',
                ParagraphStyle("up", fontSize=8, fontName="Helvetica-Bold", alignment=TA_CENTER)
            ),
            Paragraph(
                f'{ultimo.cameras_online}/{ultimo.cameras_total}' if ultimo else '–',
                estilos["body"]
            ),
        ])

    cw_nvr = [(W - 2*margin) * x for x in [0.35, 0.13, 0.13, 0.13, 0.26]]
    nvr_table = Table(nvr_rows, colWidths=cw_nvr)
    nvr_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLACK),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGRAY]),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, LGRAY),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(nvr_table)
    story.append(Spacer(1, 4*mm))

    # ── Eventos de falha ──────────────────────────────────────────────────
    story.append(Paragraph("3. EVENTOS DE FALHA NO PERÍODO", estilos["section"]))

    if not dados["eventos"]:
        story.append(Paragraph(
            "Nenhum evento de falha registrado no período.",
            ParagraphStyle("ok", fontSize=8, fontName="Helvetica",
                           textColor=GREEN, spaceAfter=6),
        ))
    else:
        ev_rows = [[
            Paragraph("Dispositivo", estilos["label"]),
            Paragraph("Tipo", estilos["label"]),
            Paragraph("Severidade", estilos["label"]),
            Paragraph("Início", estilos["label"]),
            Paragraph("Fim", estilos["label"]),
            Paragraph("Duração", estilos["label"]),
            Paragraph("Status", estilos["label"]),
        ]]
        for e in dados["eventos"]:
            ativo = e.resolvido_em is None
            sev_cor = {"critica": "EF4444", "alta": "F59E0B",
                       "media": "3B82F6", "baixa": "22C55E"}.get(e.severidade, "888888")
            ev_rows.append([
                Paragraph(e.nome_exibicao[:35], estilos["body"]),
                Paragraph(e.alvo_tipo.upper(), estilos["body"]),
                Paragraph(
                    f'<font color="#{sev_cor}"><b>{e.severidade.upper()}</b></font>',
                    ParagraphStyle("sev", fontSize=7, fontName="Helvetica-Bold", alignment=TA_CENTER)
                ),
                Paragraph(_fmt_dt(e.aberto_em), estilos["body"]),
                Paragraph(_fmt_dt(e.resolvido_em), estilos["body"]),
                Paragraph(_fmt_dur(e.duracao_minutos), estilos["body"]),
                Paragraph(
                    '<font color="#EF4444"><b>ATIVO</b></font>' if ativo
                    else '<font color="#22C55E"><b>RESOLVIDO</b></font>',
                    ParagraphStyle("st", fontSize=7, fontName="Helvetica-Bold", alignment=TA_CENTER)
                ),
            ])

        cw_ev = [(W - 2*margin) * x for x in [0.22, 0.08, 0.10, 0.16, 0.16, 0.12, 0.16]]
        ev_table = Table(ev_rows, colWidths=cw_ev)
        ev_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLACK),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGRAY]),
            ("BOX", (0, 0), (-1, -1), 0.5, GRAY),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, LGRAY),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(ev_table)

    story.append(Spacer(1, 4*mm))

    # ── Câmeras com falha ─────────────────────────────────────────────────
    cams_problema = {k: v for k, v in resumo["cameras"].items() if v["uptime_pct"] < 100}
    if cams_problema:
        story.append(Paragraph("4. CÂMERAS COM FALHA NO PERÍODO", estilos["section"]))

        cam_rows = [[
            Paragraph("NVR", estilos["label"]),
            Paragraph("Canal", estilos["label"]),
            Paragraph("Nome", estilos["label"]),
            Paragraph("Polls", estilos["label"]),
            Paragraph("Online", estilos["label"]),
            Paragraph("Uptime %", estilos["label"]),
        ]]
        for (nvr_id, ch_id), info in sorted(cams_problema.items()):
            uptime = info["uptime_pct"]
            cam_rows.append([
                Paragraph(info["nvr_id"], estilos["body"]),
                Paragraph(str(ch_id), estilos["body"]),
                Paragraph(info["nome"][:30], estilos["body"]),
                Paragraph(str(info["total_polls"]), estilos["body"]),
                Paragraph(str(info["polls_online"]), estilos["body"]),
                Paragraph(
                    f'<font color="#{"EF4444" if uptime<90 else "F59E0B"}"><b>{uptime}%</b></font>',
                    ParagraphStyle("cu", fontSize=8, fontName="Helvetica-Bold", alignment=TA_CENTER)
                ),
            ])

        cw_cam = [(W - 2*margin) * x for x in [0.20, 0.08, 0.30, 0.10, 0.10, 0.22]]
        cam_table = Table(cam_rows, colWidths=cw_cam)
        cam_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLACK),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGRAY]),
            ("BOX", (0, 0), (-1, -1), 0.5, GRAY),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, LGRAY),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(cam_table)

    # ── Rodapé ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "Grupo Ronda Porteiros LTDA · Central de Monitoramento Ronda · "
        f"Documento gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        estilos["footer"],
    ))

    def _add_page_num(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(W - margin, 10*mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=10*mm, bottomMargin=18*mm,
    )
    doc.build(story, onFirstPage=_add_page_num, onLaterPages=_add_page_num)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# Gerador Excel
# ──────────────────────────────────────────────────────────────────────────────

def _hdr_style(ws, row, cols, val, fill_hex=BLACK_HEX):
    fill = PatternFill("solid", fgColor=fill_hex)
    font = Font(bold=True, color="FFFFFF", size=9)
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.cell(row=row, column=1).value = val
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=cols)


def _row_style(cell, bold=False, color=None, align="left", bg=None):
    cell.font = Font(bold=bold, size=8, color=color or "000000")
    cell.alignment = Alignment(horizontal=align, vertical="center")
    if bg:
        cell.fill = PatternFill("solid", fgColor=bg)


def _gerar_xlsx(dt_inicio: datetime, dt_fim: datetime, dados: dict, resumo: dict) -> bytes:
    wb = openpyxl.Workbook()

    thin = Side(style="thin", color="DDDDDD")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ── Aba 1: Resumo ──────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Resumo"
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20

    gold_fill = PatternFill("solid", fgColor=GOLD_HEX)
    black_fill = PatternFill("solid", fgColor=BLACK_HEX)

    # Cabeçalho
    ws.merge_cells("A1:B1")
    ws["A1"] = "GRUPO RONDA — RELATÓRIO DE MONITORAMENTO"
    ws["A1"].font = Font(bold=True, size=13, color="FFFFFF")
    ws["A1"].fill = black_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:B2")
    ws["A2"] = f"Período: {dt_inicio.strftime('%d/%m/%Y %H:%M')} — {dt_fim.strftime('%d/%m/%Y %H:%M')}"
    ws["A2"].font = Font(bold=True, size=9, color=BLACK_HEX)
    ws["A2"].fill = PatternFill("solid", fgColor=GOLD_HEX)
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 16

    # Métricas
    metricas = [
        ("NVRs Monitorados", resumo["total_nvrs"]),
        ("Câmeras Monitoradas", resumo["total_cameras"]),
        ("Total de Eventos", resumo["total_eventos"]),
        ("Eventos Ativos", len(resumo["ativos"])),
        ("Câmeras com Falha", resumo["cameras_problema"]),
        ("Período (horas)", round(resumo["periodo_h"], 1)),
    ]
    for i, (label, val) in enumerate(metricas, start=4):
        ws.cell(row=i, column=1, value=label).font = Font(bold=True, size=9)
        c = ws.cell(row=i, column=2, value=val)
        c.font = Font(bold=True, size=11)
        c.alignment = Alignment(horizontal="center")
        if label == "Eventos Ativos" and val > 0:
            c.font = Font(bold=True, size=11, color=RED_HEX)
        elif label == "Câmeras com Falha" and val > 0:
            c.font = Font(bold=True, size=11, color=ORANGE_HEX)

    # ── Aba 2: NVRs ───────────────────────────────────────────────────────
    ws2 = wb.create_sheet("NVRs")
    hdrs = ["NVR ID", "Nome", "Total Polls", "Polls OK", "Uptime %",
            "Câm Online (último)", "Câm Offline (último)"]
    for i, h in enumerate(hdrs, 1):
        c = ws2.cell(row=1, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF", size=9)
        c.fill = black_fill
        c.alignment = Alignment(horizontal="center")
        ws2.column_dimensions[get_column_letter(i)].width = [15,25,13,10,10,18,18][i-1]

    for row_i, (nvr_id, info) in enumerate(resumo["nvrs"].items(), start=2):
        logs = info["logs"]
        ultimo = logs[-1] if logs else None
        uptime = info["uptime_pct"]
        vals = [
            nvr_id, info["nome"], info["total_polls"], info["polls_ok"],
            uptime,
            ultimo.cameras_online if ultimo else 0,
            ultimo.cameras_offline if ultimo else 0,
        ]
        bg = LGRAY_HEX if row_i % 2 == 0 else "FFFFFF"
        for col_i, val in enumerate(vals, 1):
            c = ws2.cell(row=row_i, column=col_i, value=val)
            c.fill = PatternFill("solid", fgColor=bg)
            c.alignment = Alignment(horizontal="center" if col_i > 1 else "left", vertical="center")
            c.border = border
            if col_i == 5:  # uptime
                if uptime >= 99:
                    c.font = Font(bold=True, color=GREEN_HEX)
                elif uptime >= 90:
                    c.font = Font(bold=True, color=ORANGE_HEX)
                else:
                    c.font = Font(bold=True, color=RED_HEX)

    # ── Aba 3: Eventos ────────────────────────────────────────────────────
    ws3 = wb.create_sheet("Eventos")
    hdrs3 = ["Dispositivo", "NVR ID", "Canal", "Tipo", "Severidade",
             "Início", "Fim", "Duração", "Status"]
    for i, h in enumerate(hdrs3, 1):
        c = ws3.cell(row=1, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF", size=9)
        c.fill = black_fill
        c.alignment = Alignment(horizontal="center")
        ws3.column_dimensions[get_column_letter(i)].width = [28,15,8,10,12,18,18,12,12][i-1]

    for row_i, e in enumerate(dados["eventos"], start=2):
        ativo = e.resolvido_em is None
        vals = [
            e.nome_exibicao, e.nvr_id, e.channel_id or "–",
            e.alvo_tipo.upper(), e.severidade.upper(),
            e.aberto_em.strftime("%d/%m/%Y %H:%M"),
            e.resolvido_em.strftime("%d/%m/%Y %H:%M") if e.resolvido_em else "Em aberto",
            _fmt_dur(e.duracao_minutos),
            "ATIVO" if ativo else "RESOLVIDO",
        ]
        bg = LGRAY_HEX if row_i % 2 == 0 else "FFFFFF"
        for col_i, val in enumerate(vals, 1):
            c = ws3.cell(row=row_i, column=col_i, value=val)
            c.fill = PatternFill("solid", fgColor=bg)
            c.alignment = Alignment(horizontal="center" if col_i > 1 else "left", vertical="center")
            c.border = border
            if col_i == 9:  # status
                c.font = Font(bold=True,
                              color=RED_HEX if ativo else GREEN_HEX)
            if col_i == 5:  # severidade
                sev_col = {"CRITICA": RED_HEX, "ALTA": ORANGE_HEX,
                           "MEDIA": "3B82F6", "BAIXA": GREEN_HEX}.get(str(val), DGRAY_HEX)
                c.font = Font(bold=True, color=sev_col)

    # ── Aba 4: Câmeras ────────────────────────────────────────────────────
    ws4 = wb.create_sheet("Câmeras")
    hdrs4 = ["NVR ID", "Canal", "Nome", "Total Polls", "Online", "Uptime %"]
    for i, h in enumerate(hdrs4, 1):
        c = ws4.cell(row=1, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF", size=9)
        c.fill = black_fill
        c.alignment = Alignment(horizontal="center")
        ws4.column_dimensions[get_column_letter(i)].width = [18,8,30,13,10,10][i-1]

    for row_i, ((nvr_id, ch_id), info) in enumerate(
        sorted(resumo["cameras"].items()), start=2
    ):
        uptime = info["uptime_pct"]
        vals = [nvr_id, ch_id, info["nome"],
                info["total_polls"], info["polls_online"], uptime]
        bg = LGRAY_HEX if row_i % 2 == 0 else "FFFFFF"
        for col_i, val in enumerate(vals, 1):
            c = ws4.cell(row=row_i, column=col_i, value=val)
            c.fill = PatternFill("solid", fgColor=bg)
            c.alignment = Alignment(horizontal="center" if col_i != 3 else "left",
                                    vertical="center")
            c.border = border
            if col_i == 6:
                c.font = Font(bold=True,
                              color=GREEN_HEX if uptime >= 99
                              else (ORANGE_HEX if uptime >= 90 else RED_HEX))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# Ponto de entrada público
# ──────────────────────────────────────────────────────────────────────────────

def gerar_relatorio(
    dt_inicio: datetime,
    dt_fim: datetime,
    fmt: Literal["pdf", "xlsx"] = "pdf",
) -> bytes:
    """
    Gera relatório de monitoramento no formato especificado.

    Args:
        dt_inicio: início do período (datetime, fuso local)
        dt_fim:    fim do período (datetime, fuso local)
        fmt:       "pdf" ou "xlsx"

    Returns:
        bytes do arquivo gerado
    """
    dados  = _buscar_dados(dt_inicio, dt_fim)
    resumo = _calcular_resumo(dados, dt_inicio, dt_fim)

    if fmt == "xlsx":
        return _gerar_xlsx(dt_inicio, dt_fim, dados, resumo)
    return _gerar_pdf(dt_inicio, dt_fim, dados, resumo)

"""
services/ronda_service.py — Orquestração de rondas.

Responsabilidades:
  - Criar rondas (simples e multi-NVR) via RondaRepository
  - Disparar o script de ronda em background (subprocess)
  - Montar contextos para as rotas de histórico e relatório
  - Gerenciar monitores via MonitorRepository

Não importa sqlite3, get_db, nvr_config nem queries SQL — apenas repositórios.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sqlalchemy.exc import IntegrityError

BASE_DIR = Path(__file__).resolve().parent.parent
RELATORIOS_DIR = BASE_DIR / "relatorios"

from repositories.monitor_repository import MonitorRepository
from repositories.nvr_repository import NvrRepository
from repositories.ronda_repository import RondaRepository


class RondaService:
    """Orquestra criação, consulta e execução de rondas."""

    def __init__(
        self,
        ronda_repo: RondaRepository | None = None,
        monitor_repo: MonitorRepository | None = None,
        nvr_repo: NvrRepository | None = None,
    ) -> None:
        self._ronda_repo   = ronda_repo   or RondaRepository()
        self._monitor_repo = monitor_repo or MonitorRepository()
        self._nvr_repo     = nvr_repo     or NvrRepository()

    # ── Iniciar rondas ─────────────────────────────────────────────────────

    def iniciar_ronda(self, monitor_id: int, monitor_nome: str, turno: str) -> int:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pasta = f"relatorios/ronda_{timestamp}"

        ronda = self._ronda_repo.criar(monitor_id, monitor_nome, turno, pasta)

        self._executar_background(
            "ronda.py",
            "--monitor", monitor_nome,
            "--turno", turno,
            "--pasta", pasta,
            "--ronda-id", str(ronda.id),
        )
        return ronda.id

    def iniciar_ronda_multi(
        self,
        monitor_id: int,
        monitor_nome: str,
        turno: str,
        nvr_ids: list[str] | None = None,
    ) -> int:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pasta = str(RELATORIOS_DIR / f"multi_{timestamp}")

        ronda = self._ronda_repo.criar(monitor_id, monitor_nome, turno, pasta)

        args = [
            "--monitor", monitor_nome,
            "--turno", turno,
            "--pasta", pasta,
            "--ronda-id", str(ronda.id),
        ]
        if nvr_ids:
            args.extend(["--nvrs", *nvr_ids])

        self._executar_background("ronda_multi_nvr.py", *args)
        return ronda.id

    # ── Consultas ──────────────────────────────────────────────────────────

    def listar_historico(self):
        return self._ronda_repo.listar_historico()

    def buscar_ronda(self, ronda_id: int):
        return self._ronda_repo.buscar_por_id(ronda_id)

    def status_ronda(self, ronda_id: int) -> tuple[dict, int]:
        ronda = self._ronda_repo.buscar_por_id(ronda_id)
        if not ronda:
            return {"erro": "Ronda não encontrada"}, 404

        nvrs = self._ronda_repo.listar_nvrs_por_ronda(ronda_id)
        return {
            "status": ronda.status,
            "nvrs": [
                {
                    "nvr_id":   item.nvr_id,
                    "nvr_nome": item.nvr_nome,
                    "status":   item.status,
                    "invasoes": item.invasoes,
                }
                for item in nvrs
            ],
        }, 200

    def montar_relatorio_multi_context(self, ronda_id: int) -> dict | None:
        ronda = self._ronda_repo.buscar_por_id(ronda_id)
        if not ronda:
            return None

        pasta_path = BASE_DIR / Path(ronda.pasta)
        dados      = self._carregar_dados_relatorio(pasta_path)
        pasta_name = Path(ronda.pasta).name

        return {
            "ronda":      ronda,
            "dados":      dados,
            "pasta_name": pasta_name,
            "img_prefix": f"/relatorios/{pasta_name}/imagens/",
        }

    # ── Monitores ──────────────────────────────────────────────────────────

    def listar_monitores(self):
        return self._monitor_repo.listar_todos()

    def cadastrar_monitor(self, nome: str, usuario: str, senha: str, turno: str) -> tuple[bool, str]:
        if self._monitor_repo.existe_usuario(usuario):
            return False, f"Usuário '{usuario}' já cadastrado."
        try:
            self._monitor_repo.criar(nome, usuario, senha, turno)
            return True, ""
        except IntegrityError:
            return False, "Erro de integridade ao cadastrar monitor."

    # ── NVRs ───────────────────────────────────────────────────────────────

    def quantidade_nvrs(self, nvr_ids: list[str] | None) -> int:
        """Retorna quantos NVRs serão processados na ronda."""
        if nvr_ids:
            return len(nvr_ids)
        return len(self._nvr_repo.listar(apenas_ativos=True))

    # ── Internos ───────────────────────────────────────────────────────────

    def _executar_background(self, script_name: str, *args: str) -> None:
        subprocess.Popen(
            [sys.executable, str(BASE_DIR / script_name), *args],
            cwd=BASE_DIR,
        )

    @staticmethod
    def _carregar_dados_relatorio(pasta_path: Path) -> dict | None:
        for nome_json in ("dados_multi.json", "dados.json"):
            json_path = pasta_path / nome_json
            if not json_path.exists():
                continue
            try:
                return json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

"""
services/whatsapp_service.py — Monitor de grupos WhatsApp.

Responsabilidades:
  - Validar se uma mensagem pertence ao escopo monitorado (grupos UFV/segurança)
  - Persistir mensagens e heartbeats via MensagemRepository
  - Montar o contexto para a rota /whatsapp/monitor

Não importa sqlite3, WHATSAPP_DB nem queries SQL — apenas repositórios.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from repositories.mensagem_repository import MensagemRepository


class WhatsAppMonitorService:
    """Centraliza filtro, persistência e indicadores do monitor WhatsApp."""

    # Limiar em minutos para classificar o status de um grupo
    LIMIAR_ALERTA_MIN: int = 60
    LIMIAR_CRITICO_MIN: int = 90

    def __init__(self, repo: MensagemRepository | None = None) -> None:
        self._repo = repo or MensagemRepository()

    # ── Validação de escopo ────────────────────────────────────────────────

    @staticmethod
    def grupo_valido(nome: str | None) -> bool:
        """
        Retorna True se o grupo pertence ao escopo UFV/segurança.
        Normaliza para minúsculas e remove acentos antes de comparar.
        """
        if not nome:
            return False
        normalizado = _sem_acentos(nome.lower())
        return "ufv" in normalizado and "seguranca" in normalizado

    # ── Escrita ────────────────────────────────────────────────────────────

    def registrar_mensagem(self, data: dict) -> tuple[dict, int]:
        """
        Persiste uma mensagem recebida do conector Node.js.
        Ignora silenciosamente grupos fora do escopo monitorado.
        Substitui registrar_mensagem() da versão SQLite.
        """
        grupo = data.get("grupo")
        if not self.grupo_valido(grupo):
            return {"status": "ignorado", "reason": "fora do escopo"}, 200

        self._repo.registrar(
            grupo=grupo,
            autor=data.get("autor", ""),
            data=data.get("data", datetime.utcnow().isoformat()),
            tipo=data.get("tipo", ""),
            conteudo=data.get("conteudo", ""),
            alerta="",
        )
        return {"status": "ok"}, 200

    def registrar_heartbeat(self, timestamp: str | None) -> dict:
        """
        Atualiza o timestamp do último sinal de vida do conector Node.js.
        Substitui registrar_heartbeat() da versão SQLite.
        """
        self._repo.registrar_heartbeat(timestamp)
        return {"status": "ok"}

    # ── Contexto para a rota ──────────────────────────────────────────────

    def montar_contexto_monitor(self) -> dict:
        """
        Monta o dicionário completo para o template whatsapp_monitor.html.
        Substitui montar_contexto_monitor() da versão SQLite.
        """
        agora = datetime.now()
        limite_iso = (agora - timedelta(hours=24)).isoformat()

        status_conector = self._repo.status_conector()
        sistema_online = status_conector["online"]
        ultima_verificacao = status_conector.get("ultima_verificacao")
        sistema_atraso = self._calcular_atraso(ultima_verificacao, agora)

        mensagens = self._repo.listar_recentes(limite=500)
        grupos = self._resumir_grupos(mensagens, agora)
        historico = self._montar_historico(mensagens)

        return {
            "sistema_online": sistema_online,
            "sistema_atraso": sistema_atraso,
            "grupos": grupos,
            "total_ok": sum(1 for g in grupos if g["status"] == "OK"),
            "total_alerta": sum(1 for g in grupos if g["status"] == "ALERTA"),
            "total_critico": sum(1 for g in grupos if g["status"] == "CRITICO"),
            "historico": historico,
        }

    # ── Internos ───────────────────────────────────────────────────────────

    def _resumir_grupos(self, mensagens, agora: datetime) -> list[dict]:
        """
        Agrupa as mensagens pelo nome do grupo e calcula o status de cada um
        baseado no tempo desde a última mensagem recebida.
        O primeiro registro de cada grupo é o mais recente (ORDER BY data DESC).
        """
        grupos: dict[str, dict] = {}
        for msg in mensagens:
            if msg.grupo in grupos:
                continue

            ultima = msg.data
            # msg.data pode ser datetime ou string dependendo do driver
            if isinstance(ultima, str):
                ultima = datetime.fromisoformat(ultima.replace("Z", "+00:00"))
            if ultima.tzinfo is not None:
                ultima = ultima.replace(tzinfo=None)

            inativo_min = int((agora - ultima).total_seconds() / 60)
            grupos[msg.grupo] = {
                "nome": msg.grupo,
                "ultima_msg": ultima.strftime("%d/%m/%Y %H:%M:%S"),
                "inativo_min": inativo_min,
                "status": self._status_grupo(inativo_min),
            }

        return sorted(grupos.values(), key=lambda g: g["inativo_min"], reverse=True)

    def _montar_historico(self, mensagens) -> list[dict]:
        """
        Formata as últimas 50 mensagens para exibição na tabela de histórico.
        Reaproveita a lista já carregada por montar_contexto_monitor
        para evitar uma segunda query.
        """
        historico = []
        for msg in mensagens[:50]:
            data = msg.data
            if isinstance(data, str):
                try:
                    data = datetime.fromisoformat(data.replace("Z", "+00:00"))
                except Exception:
                    pass
            if isinstance(data, datetime):
                if data.tzinfo is not None:
                    data = data.replace(tzinfo=None)
                data_formatada = data.strftime("%d/%m/%Y %H:%M:%S")
            else:
                data_formatada = str(data)

            historico.append({
                "grupo": msg.grupo,
                "autor": msg.autor,
                "data": data_formatada,
                "conteudo": msg.conteudo,
            })
        return historico

    def _status_grupo(self, minutos: int) -> str:
        if minutos > self.LIMIAR_CRITICO_MIN:
            return "CRITICO"
        if minutos > self.LIMIAR_ALERTA_MIN:
            return "ALERTA"
        return "OK"

    @staticmethod
    def _calcular_atraso(ultima_verificacao: str | None, agora: datetime) -> int | None:
        """Retorna atraso em segundos desde o último heartbeat, ou None."""
        if not ultima_verificacao:
            return None
        try:
            ultimo = datetime.fromisoformat(ultima_verificacao)
            if ultimo.tzinfo is not None:
                ultimo = ultimo.replace(tzinfo=None)
            return int((agora - ultimo).total_seconds())
        except Exception:
            return None


# ── Helpers de módulo ──────────────────────────────────────────────────────

def _sem_acentos(value: str) -> str:
    """Remove acentos comuns do português para normalização."""
    replacements = {
        "ç": "c", "ã": "a", "â": "a", "á": "a", "à": "a",
        "é": "e", "ê": "e", "í": "i", "ó": "o", "ô": "o",
        "õ": "o", "ú": "u", "ü": "u",
    }
    for acento, plain in replacements.items():
        value = value.replace(acento, plain)
    return value
