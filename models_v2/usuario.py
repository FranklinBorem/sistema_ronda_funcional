"""
models/v2/usuario.py — Usuário do sistema (substitui models/monitor.py:Monitor
no schema reconstruído) e a associação Usuario<->Unidade (escopo restrito).

Papéis (docs/security/seguranca.md): super_admin, admin_empresa, gestor,
supervisor, operador, visualizador.

super_admin não pertence a nenhuma empresa (empresa_id nullable, único
caso em que isso é permitido).
"""

from __future__ import annotations

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db

PAPEIS_VALIDOS = (
    "super_admin", "admin_empresa", "gestor",
    "supervisor", "operador", "visualizador",
)


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    empresa_id: db.Mapped[int | None] = db.mapped_column(
        db.Integer, db.ForeignKey("empresas.id"), nullable=True
    )
    nome: db.Mapped[str] = db.mapped_column(db.String(150), nullable=False)
    usuario_login: db.Mapped[str] = db.mapped_column(db.String(80), nullable=False)
    senha_hash: db.Mapped[str] = db.mapped_column(db.String(255), nullable=False)
    papel: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False)
    status: db.Mapped[str] = db.mapped_column(
        db.String(20), nullable=False, default="ativo"
    )
    criado_em: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "empresa_id", "usuario_login", name="uq_usuarios_empresa_login"
        ),
        db.CheckConstraint(
            "papel IN ('super_admin','admin_empresa','gestor','supervisor',"
            "'operador','visualizador')",
            name="ck_usuarios_papel",
        ),
        db.CheckConstraint("status IN ('ativo','inativo')", name="ck_usuarios_status"),
    )

    # ── Relacionamentos ─────────────────────────────────────────────────
    empresa: db.Mapped["Empresa | None"] = db.relationship(  # type: ignore[name-defined]
        "Empresa", back_populates="usuarios"
    )
    unidades_escopo: db.Mapped[list["Unidade"]] = db.relationship(  # type: ignore[name-defined]
        "Unidade", secondary="usuario_unidade", back_populates="usuarios_escopo"
    )

    # ── Senha ────────────────────────────────────────────────────────────
    def set_senha(self, senha_plain: str) -> None:
        """Gera hash e armazena. Nunca armazene senha em texto plano."""
        self.senha_hash = generate_password_hash(senha_plain)

    def verificar_senha(self, senha_plain: str) -> bool:
        return check_password_hash(self.senha_hash, senha_plain)

    def __repr__(self) -> str:
        return (
            f"<Usuario id={self.id} login={self.usuario_login!r} "
            f"papel={self.papel!r} empresa_id={self.empresa_id}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "empresa_id": self.empresa_id,
            "nome": self.nome,
            "usuario_login": self.usuario_login,
            "papel": self.papel,
            "status": self.status,
        }


class UsuarioUnidade(db.Model):
    """
    Associativa N:N — só populada para papéis de escopo restrito
    (supervisor/operador). Ausência de linhas = sem restrição adicional
    (admin_empresa/gestor têm escopo = empresa inteira, implícito).
    """
    __tablename__ = "usuario_unidade"

    usuario_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), primary_key=True
    )
    unidade_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("unidades.id"), primary_key=True
    )

    def __repr__(self) -> str:
        return f"<UsuarioUnidade usuario_id={self.usuario_id} unidade_id={self.unidade_id}>"
