"""
models/monitor.py — Usuários do sistema (monitores de segurança).

Mapeamento da tabela `monitores` para SQLAlchemy ORM.
"""

from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class Monitor(db.Model):
    __tablename__ = "monitores"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    nome: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False)
    usuario: db.Mapped[str] = db.mapped_column(
        db.String(60), nullable=False, unique=True, index=True
    )
    senha: db.Mapped[str] = db.mapped_column(db.String(256), nullable=False)
    turno: db.Mapped[str] = db.mapped_column(db.String(60), nullable=False)

    # ── Relacionamentos ────────────────────────────────────────────────────
    rondas: db.Mapped[list["Ronda"]] = db.relationship(  # type: ignore[name-defined]
        "Ronda", back_populates="monitor", lazy="dynamic"
    )

    # ── Métodos de senha ───────────────────────────────────────────────────

    def set_senha(self, senha_plain: str) -> None:
        """Gera hash e armazena. Nunca armazene senha em texto plano."""
        self.senha = generate_password_hash(senha_plain)

    def verificar_senha(self, senha_plain: str) -> bool:
        """Retorna True se a senha bate com o hash armazenado."""
        return check_password_hash(self.senha, senha_plain)

    # ── Representação ──────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"<Monitor id={self.id} usuario={self.usuario!r} turno={self.turno!r}>"

    def to_dict(self) -> dict:
        return {
            "id":     self.id,
            "nome":   self.nome,
            "usuario": self.usuario,
            "turno":  self.turno,
        }
