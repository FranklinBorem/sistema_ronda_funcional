"""
models/mensagem.py — Mensagens WhatsApp e status do conector Node.js.

Substitui as tabelas `mensagens` e `status_sistema` do mensagens.db.
Consolidado no banco principal (PostgreSQL) para eliminar o segundo
arquivo SQLite separado.
"""

from __future__ import annotations

from datetime import datetime

from extensions import db


class Mensagem(db.Model):
    __tablename__ = "mensagens"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)

    grupo: db.Mapped[str | None] = db.mapped_column(
        db.String(200), nullable=True, index=True
    )
    autor: db.Mapped[str | None] = db.mapped_column(db.String(200), nullable=True)

    # ISO 8601 vindo do Node.js — armazenado como DateTime no Postgres
    data: db.Mapped[datetime | None] = db.mapped_column(
        db.DateTime, nullable=True, index=True
    )

    tipo: db.Mapped[str | None] = db.mapped_column(
        db.String(30), nullable=True          # "chat", "image", "audio", etc.
    )
    conteudo: db.Mapped[str | None] = db.mapped_column(db.Text, nullable=True)

    # Classificação de alerta feita pelo sistema — ex: "urgente", ""
    alerta: db.Mapped[str] = db.mapped_column(
        db.String(60), nullable=False, default=""
    )

    def __repr__(self) -> str:
        return (
            f"<Mensagem id={self.id} grupo={self.grupo!r} "
            f"autor={self.autor!r} tipo={self.tipo!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id":       self.id,
            "grupo":    self.grupo,
            "autor":    self.autor,
            "data":     self.data.isoformat() if self.data else None,
            "tipo":     self.tipo,
            "conteudo": self.conteudo,
            "alerta":   self.alerta,
        }


class StatusSistema(db.Model):
    """
    Linha única que registra o último heartbeat recebido do conector WhatsApp.
    Sempre id=1 — use StatusSistema.get() para acessar.
    """
    __tablename__ = "status_sistema"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    ultima_verificacao_sistema: db.Mapped[datetime | None] = db.mapped_column(
        db.DateTime, nullable=True
    )

    @classmethod
    def get(cls) -> "StatusSistema":
        """
        Retorna a linha de status (id=1), criando-a se não existir.
        Deve ser chamado dentro de um contexto de aplicação Flask.
        """
        instance = db.session.get(cls, 1)
        if instance is None:
            instance = cls(id=1, ultima_verificacao_sistema=datetime.utcnow())
            db.session.add(instance)
            db.session.commit()
        return instance

    def atualizar(self, timestamp: datetime | None = None) -> None:
        self.ultima_verificacao_sistema = timestamp or datetime.utcnow()

    def __repr__(self) -> str:
        return f"<StatusSistema ultima={self.ultima_verificacao_sistema!r}>"
