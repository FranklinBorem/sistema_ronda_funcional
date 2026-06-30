"""
repositories/mensagem_repository.py — Acesso a dados de mensagens WhatsApp.

Substitui as queries inline de:
  - whatsapp_routes.py (receber_mensagem, heartbeat, montar_contexto_monitor)
  - services/whatsapp_service.py

Consolida também o StatusSistema (heartbeat do Node.js) que antes ficava
num banco SQLite separado (mensagens.db).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import desc

from models.mensagem import Mensagem, StatusSistema
from .base import BaseRepository


class MensagemRepository(BaseRepository):

    # ── Mensagens ──────────────────────────────────────────────────────────

    def registrar(
        self,
        grupo: str,
        autor: str,
        data: datetime,
        tipo: str,
        conteudo: str,
        alerta: str = "",
    ) -> Mensagem:
        """
        Persiste uma mensagem recebida do conector Node.js.
        Converte string ISO 8601 para datetime se necessário.
        """
        if isinstance(data, str):
            data = datetime.fromisoformat(data.replace("Z", "+00:00"))

        msg = Mensagem(
            grupo=grupo,
            autor=autor,
            data=data,
            tipo=tipo,
            conteudo=conteudo,
            alerta=alerta,
        )
        self.session.add(msg)
        self.session.flush()
        return msg

    def listar_recentes(
        self,
        limite: int = 100,
        grupo: str | None = None,
        apenas_alertas: bool = False,
    ) -> list[Mensagem]:
        q = self.session.query(Mensagem)

        if grupo:
            q = q.filter(Mensagem.grupo == grupo)
        if apenas_alertas:
            q = q.filter(Mensagem.alerta != "")

        return (
            q.order_by(desc(Mensagem.data))
            .limit(limite)
            .all()
        )

    def listar_grupos(self) -> list[str]:
        """Grupos distintos monitorados — para filtros na UI."""
        rows = (
            self.session
            .query(Mensagem.grupo)
            .filter(Mensagem.grupo.isnot(None))
            .distinct()
            .order_by(Mensagem.grupo)
            .all()
        )
        return [r.grupo for r in rows]

    def contar_por_grupo(self, horas: int = 24) -> list[dict]:
        """Mensagens por grupo nas últimas N horas — widget do monitor."""
        from sqlalchemy import func
        corte = datetime.utcnow() - timedelta(hours=horas)
        rows = (
            self.session
            .query(Mensagem.grupo, func.count(Mensagem.id).label("total"))
            .filter(Mensagem.data >= corte)
            .group_by(Mensagem.grupo)
            .order_by(desc("total"))
            .all()
        )
        return [{"grupo": r.grupo, "total": r.total} for r in rows]

    def ultima_mensagem(self) -> Optional[Mensagem]:
        return (
            self.session
            .query(Mensagem)
            .order_by(desc(Mensagem.data))
            .first()
        )

    # ── Status do sistema (heartbeat) ─────────────────────────────────────

    def registrar_heartbeat(self, timestamp: datetime | str | None = None) -> None:
        """
        Atualiza o timestamp do último heartbeat do conector Node.js.
        Cria a linha de status se não existir (id=1).
        """
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                timestamp = datetime.utcnow()

        status = self.session.get(StatusSistema, 1)
        if status is None:
            status = StatusSistema(id=1)
            self.session.add(status)

        status.atualizar(timestamp)

    def status_conector(self) -> dict:
        """
        Retorna estado do conector WhatsApp:
          - online: True se o último heartbeat foi há menos de 2 minutos
          - ultima_verificacao: timestamp ISO ou None
        """
        status = self.session.get(StatusSistema, 1)
        if status is None or status.ultima_verificacao_sistema is None:
            return {"online": False, "ultima_verificacao": None}

        delta = datetime.utcnow() - status.ultima_verificacao_sistema
        return {
            "online": delta.total_seconds() < 120,
            "ultima_verificacao": status.ultima_verificacao_sistema.isoformat(),
        }
