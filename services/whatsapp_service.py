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
