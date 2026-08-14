"""
models/v2/unidade.py — Unidade (site físico monitorado) e Área (subdivisão
opcional). Substitui o campo texto livre `site` de models/nvr.py e
models/nvr_monitorado.py no schema antigo.
"""

from __future__ import annotations

from extensions import db


class Unidade(db.Model):
    __tablename__ = "unidades"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    empresa_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("empresas.id"), nullable=False
    )
    nome: db.Mapped[str] = db.mapped_column(db.String(150), nullable=False)
    localizacao: db.Mapped[str | None] = db.mapped_column(db.String(250), nullable=True)
    status: db.Mapped[str] = db.mapped_column(
        db.String(20), nullable=False, default="ativa"
    )

    __table_args__ = (
        db.CheckConstraint("status IN ('ativa','inativa')", name="ck_unidades_status"),
        db.Index("ix_unidades_empresa_id", "empresa_id"),
    )

    # ── Relacionamentos ─────────────────────────────────────────────────
    empresa: db.Mapped["Empresa"] = db.relationship(  # type: ignore[name-defined]
        "Empresa", back_populates="unidades"
    )
    areas: db.Mapped[list["Area"]] = db.relationship(
        "Area", back_populates="unidade", cascade="all, delete-orphan"
    )
    nvrs: db.Mapped[list["Nvr"]] = db.relationship(  # type: ignore[name-defined]
        "Nvr", back_populates="unidade", cascade="all, delete-orphan"
    )
    rondas: db.Mapped[list["Ronda"]] = db.relationship(  # type: ignore[name-defined]
        "Ronda", back_populates="unidade"
    )
    usuarios_escopo: db.Mapped[list["Usuario"]] = db.relationship(  # type: ignore[name-defined]
        "Usuario", secondary="usuario_unidade", back_populates="unidades_escopo"
    )

    def __repr__(self) -> str:
        return f"<Unidade id={self.id} nome={self.nome!r} empresa_id={self.empresa_id}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "empresa_id": self.empresa_id,
            "nome": self.nome,
            "localizacao": self.localizacao,
            "status": self.status,
        }


class Area(db.Model):
    """Subdivisão opcional dentro de uma Unidade (ex.: "Pátio de painéis")."""
    __tablename__ = "areas"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    unidade_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("unidades.id"), nullable=False
    )
    nome: db.Mapped[str] = db.mapped_column(db.String(100), nullable=False)

    unidade: db.Mapped["Unidade"] = db.relationship("Unidade", back_populates="areas")

    def __repr__(self) -> str:
        return f"<Area id={self.id} nome={self.nome!r} unidade_id={self.unidade_id}>"
