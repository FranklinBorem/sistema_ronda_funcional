"""
models/v2/empresa.py — Empresa (tenant) e sua ligação com Plano.

Ver docs/database/modelo-banco.md e docs/database/multi-tenancy.md
para a decisão de banco compartilhado + empresa_id (row-level).
"""

from __future__ import annotations

from datetime import datetime, timezone

from extensions import db


class Empresa(db.Model):
    __tablename__ = "empresas"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    nome: db.Mapped[str] = db.mapped_column(db.String(200), nullable=False)
    slug: db.Mapped[str] = db.mapped_column(
        db.String(80), nullable=False, unique=True, index=True
    )
    status: db.Mapped[str] = db.mapped_column(
        db.String(20), nullable=False, default="ativa"
    )
    plano_id: db.Mapped[int | None] = db.mapped_column(
        db.Integer, db.ForeignKey("planos.id"), nullable=True
    )
    criado_em: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.CheckConstraint("status IN ('ativa','suspensa')", name="ck_empresas_status"),
    )

    # ── Relacionamentos ─────────────────────────────────────────────────
    plano: db.Mapped["Plano | None"] = db.relationship("Plano")  # type: ignore[name-defined]
    unidades: db.Mapped[list["Unidade"]] = db.relationship(  # type: ignore[name-defined]
        "Unidade", back_populates="empresa", cascade="all, delete-orphan"
    )
    usuarios: db.Mapped[list["Usuario"]] = db.relationship(  # type: ignore[name-defined]
        "Usuario", back_populates="empresa", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Empresa id={self.id} slug={self.slug!r} status={self.status!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "slug": self.slug,
            "status": self.status,
            "plano_id": self.plano_id,
        }
