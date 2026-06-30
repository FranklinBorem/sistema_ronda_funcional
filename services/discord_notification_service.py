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
