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
