"""
models/v2/plano.py — Limites e features contratados por uma Empresa.

Estrutura pronta para receber regra comercial futura (RF20/Could Have,
ver docs/requirements/requisitos.md) sem hardcode de billing agora.
"""

from __future__ import annotations

from extensions import db


class Plano(db.Model):
    __tablename__ = "planos"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    nome: db.Mapped[str] = db.mapped_column(db.String(60), nullable=False)
    limites: db.Mapped[dict] = db.mapped_column(
        db.JSON, nullable=False, default=dict
    )  # ex.: {"max_cameras": 50, "max_unidades": 5}
    features: db.Mapped[dict] = db.mapped_column(
        db.JSON, nullable=False, default=dict
    )  # ex.: {"whatsapp": true, "ia_veiculo": false}

    def __repr__(self) -> str:
        return f"<Plano id={self.id} nome={self.nome!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "limites": self.limites,
            "features": self.features,
        }
