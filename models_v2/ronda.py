"""
models/v2/ronda.py — Execução de ronda (Ronda) e resultado por NVR
(ResultadoRonda). Evolução de models/ronda.py:Ronda/RondaNvr, agora
com unidade_id no lugar da referência solta a NVRs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from extensions import db

STATUS_RONDA_VALIDOS = ("em_andamento", "finalizada", "com_alertas", "erro")


class Ronda(db.Model):
    __tablename__ = "rondas"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    unidade_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("unidades.id"), nullable=False
    )
    usuario_id: db.Mapped[int | None] = db.mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=True
    )
    status: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False)
    iniciado_em: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    finalizado_em: db.Mapped[datetime | None] = db.mapped_column(
        db.DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('em_andamento','finalizada','com_alertas','erro')",
            name="ck_rondas_status",
        ),
        db.Index("ix_rondas_unidade_iniciado", "unidade_id", "iniciado_em"),
    )

    # ── Relacionamentos ─────────────────────────────────────────────────
    unidade: db.Mapped["Unidade"] = db.relationship(  # type: ignore[name-defined]
        "Unidade", back_populates="rondas"
    )
    usuario: db.Mapped["Usuario | None"] = db.relationship("Usuario")  # type: ignore[name-defined]
    resultados: db.Mapped[list["ResultadoRonda"]] = db.relationship(
        "ResultadoRonda", back_populates="ronda", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Ronda id={self.id} unidade_id={self.unidade_id} status={self.status!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "unidade_id": self.unidade_id,
            "usuario_id": self.usuario_id,
            "status": self.status,
            "iniciado_em": self.iniciado_em.isoformat() if self.iniciado_em else None,
            "finalizado_em": self.finalizado_em.isoformat() if self.finalizado_em else None,
        }


class ResultadoRonda(db.Model):
    __tablename__ = "resultados_ronda"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    ronda_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("rondas.id"), nullable=False
    )
    nvr_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("nvrs.id"), nullable=False
    )
    status: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False)
    imagens_ref: db.Mapped[dict | None] = db.mapped_column(db.JSON, nullable=True)

    ronda: db.Mapped["Ronda"] = db.relationship("Ronda", back_populates="resultados")
    nvr: db.Mapped["Nvr"] = db.relationship("Nvr")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<ResultadoRonda id={self.id} ronda_id={self.ronda_id} nvr_id={self.nvr_id}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ronda_id": self.ronda_id,
            "nvr_id": self.nvr_id,
            "status": self.status,
            "imagens_ref": self.imagens_ref,
        }
