"""
models/v2/notificacao.py — Integracao (config de canal por empresa:
Discord/e-mail/WhatsApp) e Notificacao (registro do que foi enviado,
para auditoria de alertas).
"""

from __future__ import annotations

from datetime import datetime, timezone

from extensions import db

TIPOS_INTEGRACAO_VALIDOS = ("discord", "email", "whatsapp")


class Integracao(db.Model):
    __tablename__ = "integracoes"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    empresa_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("empresas.id"), nullable=False
    )
    tipo: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False)
    configuracao: db.Mapped[dict] = db.mapped_column(db.JSON, nullable=False)
    ativo: db.Mapped[bool] = db.mapped_column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.UniqueConstraint("empresa_id", "tipo", name="uq_integracoes_empresa_tipo"),
        db.CheckConstraint(
            "tipo IN ('discord','email','whatsapp')", name="ck_integracoes_tipo"
        ),
    )

    empresa: db.Mapped["Empresa"] = db.relationship("Empresa")  # type: ignore[name-defined]
    notificacoes: db.Mapped[list["Notificacao"]] = db.relationship(
        "Notificacao", back_populates="integracao"
    )

    def __repr__(self) -> str:
        return f"<Integracao id={self.id} empresa_id={self.empresa_id} tipo={self.tipo!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "empresa_id": self.empresa_id,
            "tipo": self.tipo,
            "ativo": self.ativo,
            # configuracao não incluída deliberadamente — pode conter
            # segredo (token/webhook); ver docs/security/seguranca.md.
        }


class Notificacao(db.Model):
    __tablename__ = "notificacoes"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    ocorrencia_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("ocorrencias.id"), nullable=False
    )
    integracao_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("integracoes.id"), nullable=False
    )
    enviado_em: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    status_envio: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False)

    ocorrencia: db.Mapped["Ocorrencia"] = db.relationship(  # type: ignore[name-defined]
        "Ocorrencia", back_populates="notificacoes"
    )
    integracao: db.Mapped["Integracao"] = db.relationship(
        "Integracao", back_populates="notificacoes"
    )

    def __repr__(self) -> str:
        return f"<Notificacao id={self.id} ocorrencia_id={self.ocorrencia_id} status={self.status_envio!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ocorrencia_id": self.ocorrencia_id,
            "integracao_id": self.integracao_id,
            "enviado_em": self.enviado_em.isoformat() if self.enviado_em else None,
            "status_envio": self.status_envio,
        }
