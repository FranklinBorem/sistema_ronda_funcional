"""
models/v2/auditoria.py — Log de ações administrativas sensíveis.
Foco em escrita/configuração, não em leitura (ver docs/security/seguranca.md).
"""

from __future__ import annotations

from datetime import datetime, timezone

from extensions import db


class Auditoria(db.Model):
    __tablename__ = "auditoria"

    id: db.Mapped[int] = db.mapped_column(db.BigInteger, primary_key=True)
    empresa_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("empresas.id"), nullable=False
    )
    usuario_id: db.Mapped[int | None] = db.mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=True
    )
    acao: db.Mapped[str] = db.mapped_column(db.String(60), nullable=False)
    entidade: db.Mapped[str] = db.mapped_column(db.String(60), nullable=False)
    entidade_id: db.Mapped[int | None] = db.mapped_column(db.Integer, nullable=True)
    detalhes: db.Mapped[dict | None] = db.mapped_column(db.JSON, nullable=True)
    timestamp: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_auditoria_empresa_timestamp", "empresa_id", "timestamp"),
    )

    empresa: db.Mapped["Empresa"] = db.relationship("Empresa")  # type: ignore[name-defined]
    usuario: db.Mapped["Usuario | None"] = db.relationship("Usuario")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Auditoria id={self.id} acao={self.acao!r} entidade={self.entidade!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "empresa_id": self.empresa_id,
            "usuario_id": self.usuario_id,
            "acao": self.acao,
            "entidade": self.entidade,
            "entidade_id": self.entidade_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
