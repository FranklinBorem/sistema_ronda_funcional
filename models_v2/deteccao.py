"""
models/v2/deteccao.py — RegraDeteccao e EventoIA.

Peça central da evolução de IA (docs/architecture/ia.md): o motor de
ronda passa a consultar "quais regras esta câmera tem" em vez de ter
a detecção de pessoa fixa no código — permite adicionar novos tipos
de detecção sem alterar core/ronda_multi_nvr.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from extensions import db


class RegraDeteccao(db.Model):
    __tablename__ = "regras_deteccao"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    camera_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("cameras.id"), nullable=False
    )
    tipo: db.Mapped[str] = db.mapped_column(db.String(40), nullable=False)
    parametros: db.Mapped[dict] = db.mapped_column(
        db.JSON, nullable=False, default=dict
    )  # ex.: {"conf_threshold": 0.30, "roi": [...]}
    ativo: db.Mapped[bool] = db.mapped_column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.Index("ix_regras_deteccao_camera_tipo", "camera_id", "tipo"),
    )

    camera: db.Mapped["Camera"] = db.relationship(  # type: ignore[name-defined]
        "Camera", back_populates="regras_deteccao"
    )
    eventos: db.Mapped[list["EventoIA"]] = db.relationship(
        "EventoIA", back_populates="regra"
    )

    def __repr__(self) -> str:
        return f"<RegraDeteccao id={self.id} camera_id={self.camera_id} tipo={self.tipo!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "tipo": self.tipo,
            "parametros": self.parametros,
            "ativo": self.ativo,
        }


class EventoIA(db.Model):
    """Uma detecção bruta. Nem todo EventoIA vira Ocorrência (ocorrencia_id nullable)."""
    __tablename__ = "eventos_ia"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    camera_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("cameras.id"), nullable=False
    )
    regra_id: db.Mapped[int | None] = db.mapped_column(
        db.Integer, db.ForeignKey("regras_deteccao.id"), nullable=True
    )
    classe: db.Mapped[str] = db.mapped_column(db.String(40), nullable=False)
    confianca: db.Mapped[Decimal] = db.mapped_column(db.Numeric(5, 4), nullable=False)
    evidencia_ref: db.Mapped[str | None] = db.mapped_column(db.String(255), nullable=True)
    ocorrencia_id: db.Mapped[int | None] = db.mapped_column(
        db.Integer, db.ForeignKey("ocorrencias.id"), nullable=True
    )
    timestamp: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_eventos_ia_camera_timestamp", "camera_id", "timestamp"),
    )

    camera: db.Mapped["Camera"] = db.relationship("Camera")  # type: ignore[name-defined]
    regra: db.Mapped["RegraDeteccao | None"] = db.relationship(
        "RegraDeteccao", back_populates="eventos"
    )
    ocorrencia: db.Mapped["Ocorrencia | None"] = db.relationship(  # type: ignore[name-defined]
        "Ocorrencia", back_populates="eventos_ia"
    )

    def __repr__(self) -> str:
        return (
            f"<EventoIA id={self.id} camera_id={self.camera_id} "
            f"classe={self.classe!r} confianca={self.confianca}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "regra_id": self.regra_id,
            "classe": self.classe,
            "confianca": float(self.confianca),
            "evidencia_ref": self.evidencia_ref,
            "ocorrencia_id": self.ocorrencia_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
