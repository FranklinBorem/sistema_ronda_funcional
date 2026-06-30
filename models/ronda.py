"""
models/ronda.py — Rondas de segurança e resultados por NVR.

Tabelas:
    rondas      — ronda "pai" iniciada por um monitor
    rondas_nvr  — resultado de cada NVR dentro de uma ronda
"""

from __future__ import annotations

import enum
from datetime import datetime

from extensions import db


# ── Enums ──────────────────────────────────────────────────────────────────

class StatusRonda(str, enum.Enum):
    EM_ANDAMENTO = "em_andamento"
    FINALIZADA   = "finalizada"
    COM_ALERTAS  = "com_alertas"
    ERRO         = "erro"


class StatusRondaNvr(str, enum.Enum):
    EM_ANDAMENTO = "em_andamento"
    FINALIZADA   = "finalizada"
    COM_ALERTAS  = "com_alertas"
    ERRO         = "erro"


# ── Models ─────────────────────────────────────────────────────────────────

class Ronda(db.Model):
    """
    Ronda pai — criada a cada ciclo do loop ou manualmente pelo monitor.
    Uma ronda pode conter N RondaNvr (uma por NVR processado).
    """
    __tablename__ = "rondas"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)

    # Chave estrangeira para o monitor responsável
    monitor_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("monitores.id"), nullable=False, index=True
    )
    monitor_nome: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False)
    turno: db.Mapped[str] = db.mapped_column(db.String(60), nullable=False)

    iniciada_em: db.Mapped[datetime] = db.mapped_column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )
    finalizada_em: db.Mapped[datetime | None] = db.mapped_column(
        db.DateTime, nullable=True
    )

    # Pasta relativa onde os relatórios/imagens desta ronda estão salvos
    pasta: db.Mapped[str | None] = db.mapped_column(db.Text, nullable=True)

    status: db.Mapped[str] = db.mapped_column(
        db.String(30),
        nullable=False,
        default=StatusRonda.EM_ANDAMENTO.value,
        index=True,
    )

    # ── Relacionamentos ────────────────────────────────────────────────────
    monitor: db.Mapped["Monitor"] = db.relationship(  # type: ignore[name-defined]
        "Monitor", back_populates="rondas"
    )
    nvrs: db.Mapped[list["RondaNvr"]] = db.relationship(
        "RondaNvr", back_populates="ronda", cascade="all, delete-orphan"
    )
    alertas: db.Mapped[list["Alerta"]] = db.relationship(  # type: ignore[name-defined]
        "Alerta", back_populates="ronda", cascade="all, delete-orphan"
    )

    # ── Helpers ────────────────────────────────────────────────────────────

    def finalizar(self, status: StatusRonda = StatusRonda.FINALIZADA) -> None:
        self.status = status.value
        self.finalizada_em = datetime.utcnow()

    @property
    def total_invasoes(self) -> int:
        return sum(n.invasoes for n in self.nvrs)

    def __repr__(self) -> str:
        return f"<Ronda id={self.id} monitor={self.monitor_nome!r} status={self.status!r}>"

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "monitor_id":    self.monitor_id,
            "monitor_nome":  self.monitor_nome,
            "turno":         self.turno,
            "iniciada_em":   self.iniciada_em.isoformat() if self.iniciada_em else None,
            "finalizada_em": self.finalizada_em.isoformat() if self.finalizada_em else None,
            "pasta":         self.pasta,
            "status":        self.status,
        }


class RondaNvr(db.Model):
    """
    Resultado de um NVR dentro de uma ronda.
    Criado após a conclusão da thread de cada NVR.
    """
    __tablename__ = "rondas_nvr"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)

    ronda_id: db.Mapped[int | None] = db.mapped_column(
        db.Integer, db.ForeignKey("rondas.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    nvr_id: db.Mapped[str] = db.mapped_column(db.String(60), nullable=False, index=True)
    nvr_nome: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False)

    status: db.Mapped[str] = db.mapped_column(
        db.String(30),
        nullable=False,
        default=StatusRondaNvr.EM_ANDAMENTO.value,
    )
    invasoes: db.Mapped[int] = db.mapped_column(db.Integer, default=0, nullable=False)
    pasta: db.Mapped[str | None] = db.mapped_column(db.Text, nullable=True)
    finalizada_em: db.Mapped[datetime | None] = db.mapped_column(
        db.DateTime, nullable=True
    )

    # ── Relacionamento ─────────────────────────────────────────────────────
    ronda: db.Mapped["Ronda"] = db.relationship("Ronda", back_populates="nvrs")

    def __repr__(self) -> str:
        return (
            f"<RondaNvr id={self.id} nvr_id={self.nvr_id!r} "
            f"invasoes={self.invasoes} status={self.status!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "ronda_id":      self.ronda_id,
            "nvr_id":        self.nvr_id,
            "nvr_nome":      self.nvr_nome,
            "status":        self.status,
            "invasoes":      self.invasoes,
            "pasta":         self.pasta,
            "finalizada_em": self.finalizada_em.isoformat() if self.finalizada_em else None,
        }
