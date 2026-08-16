"""
services_v2/notificacao_service.py — Envio de notificações a partir
de Ocorrencia, resolvendo a configuração por EMPRESA (Integracao) em
vez de uma variável global do processo — corrige, por construção, o
problema original identificado no início da análise deste projeto
(webhook Discord hardcoded/global em config.py).

Adaptado de services/discord_notification_service.py (lógica de
payload/envio preservada; a mudança real é de ONDE a configuração
vem: antes app.config global, agora Integracao por empresa).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

_COR = {"baixa": 0x95A5A6, "media": 0xF1C40F, "alta": 0xE67E22, "critica": 0xE74C3C, "ok": 0x2ECC71}
_EMOJI = {"deteccao_ia": "🚨", "falha_equipamento": "📡", "manual": "📝", "mensagem_externa": "💬"}


def _montar_payload_discord(ocorrencia, resolucao: bool) -> dict[str, Any]:
    """Monta o payload do webhook a partir de uma Ocorrencia (models_v2)."""
    emoji = _EMOJI.get(ocorrencia.origem, "⚠️")

    if resolucao:
        cor = _COR["ok"]
        titulo = f"✅ RESOLVIDO — Ocorrência #{ocorrencia.id}"
        status_linha = (
            f"**Status:** Resolvido às "
            f"`{ocorrencia.tratado_em.strftime('%H:%M:%S') if ocorrencia.tratado_em else 'agora'}`"
        )
    else:
        cor = _COR.get(ocorrencia.prioridade, _COR["media"])
        titulo = f"{emoji} ALERTA — Ocorrência #{ocorrencia.id}"
        status_linha = f"**Prioridade:** {ocorrencia.prioridade.upper()}"

    duracao_linha = ""
    if resolucao and ocorrencia.aberto_em and ocorrencia.tratado_em:
        delta = ocorrencia.tratado_em - ocorrencia.aberto_em
        duracao_linha = f"\n**Duração:** `{int(delta.total_seconds() // 60)} min`"

    descricao = "\n".join(filter(None, [
        f"**Origem:** `{ocorrencia.origem}`",
        f"**Tipo:** `{ocorrencia.tipo}`" if ocorrencia.tipo else "",
        status_linha,
        f"**Aberto em:** `{ocorrencia.aberto_em.strftime('%d/%m/%Y %H:%M:%S')}`",
        duracao_linha,
    ]))

    return {
        "username": "Vigilante IA",
        "embeds": [{
            "title": titulo,
            "description": descricao,
            "color": cor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": f"Unidade #{ocorrencia.unidade_id}"},
        }],
    }


class NotificacaoService:
    """
    Resolve a Integracao ativa de uma empresa e envia a notificação.
    Registra o resultado em Notificacao (repositories_v2).
    """

    def __init__(self, integracao_repo=None, session=None):
        from repositories_v2.ocorrencia_repository import IntegracaoRepository
        self._integracao_repo = integracao_repo or IntegracaoRepository(session=session)

    def notificar_ocorrencia(self, ocorrencia, resolucao: bool = False) -> bool:
        integracao = self._integracao_repo.buscar_ativa(ocorrencia.empresa_id, "discord")
        if integracao is None:
            logger.debug(
                "Nenhuma integração Discord ativa para empresa_id=%s — nada enviado.",
                ocorrencia.empresa_id,
            )
            return False

        webhook_url = integracao.configuracao.get("webhook_url")
        if not webhook_url:
            logger.warning(
                "Integracao id=%s (empresa_id=%s) sem webhook_url configurado.",
                integracao.id, ocorrencia.empresa_id,
            )
            return False

        payload = _montar_payload_discord(ocorrencia, resolucao)
        enviado = self._post(webhook_url, payload)

        self._integracao_repo.registrar_notificacao(
            ocorrencia_id=ocorrencia.id,
            integracao_id=integracao.id,
            status_envio="enviado" if enviado else "falhou",
        )
        return enviado

    @staticmethod
    def _post(webhook_url: str, payload: dict) -> bool:
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            return resp.status_code in (200, 204)
        except requests.exceptions.RequestException as e:
            logger.error("Falha de rede ao enviar notificação Discord: %s", e)
            return False
