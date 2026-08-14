"""
models/v2/ocorrencia.py — Ocorrência: unifica models/alerta.py:Alerta
(detecção de IA) e models/monitoring.py:MonitorEvent (falha de
equipamento) do schema antigo em um único conceito de negócio, com
tratativa (responsável, status, tempos de resposta/resolução).
"""

from __future__ import annotations

from datetime import datetime, timezone

from extensions import db

ORIGENS_VALIDAS = ("deteccao_ia", "falha_equipamento", "manual", "mensagem_externa")


class Ocorrencia(db.Model):
    __tablename__ = "ocorrencias"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    # empresa_id duplicado deliberadamente aqui (não só via unidade_id) —
    # evita JOIN obrigatório em toda política de Row-Level Security,
    # já que ocorrencias é a tabela mais consultada por filtro de
    # dashboard/tenant. Ver docs/database/modelo-banco.md.
    empresa_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("empresas.id"), nullable=False
    )
    unidade_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("unidades.id"), nullable=False
    )
    origem: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False)
    tipo: db.Mapped[str | None] = db.mapped_column(db.String(40), nullable=True)
    prioridade: db.Mapped[str] = db.mapped_column(
        db.String(10), nullable=False, default="media"
    )
    status: db.Mapped[str] = db.mapped_column(
        db.String(20), nullable=False, default="aberta"
    )
    responsavel_id: db.Mapped[int | None] = db.mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=True
    )
    aberto_em: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    tratado_em: db.Mapped[datetime | None] = db.mapped_column(
        db.DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        db.CheckConstraint(
            "origem IN ('deteccao_ia','falha_equipamento','manual','mensagem_externa')",
            name="ck_ocorrencias_origem",
        ),
        db.Index("ix_ocorrencias_empresa_status", "empresa_id", "status"),
        db.Index("ix_ocorrencias_unidade_aberto", "unidade_id", "aberto_em"),
    )

    # ── Relacionamentos ─────────────────────────────────────────────────
    empresa: db.Mapped["Empresa"] = db.relationship("Empresa")  # type: ignore[name-defined]
    unidade: db.Mapped["Unidade"] = db.relationship("Unidade")  # type: ignore[name-defined]
    responsavel: db.Mapped["Usuario | None"] = db.relationship("Usuario")  # type: ignore[name-defined]
    eventos_ia: db.Mapped[list["EventoIA"]] = db.relationship(  # type: ignore[name-defined]
        "EventoIA", back_populates="ocorrencia"
    )
    notificacoes: db.Mapped[list["Notificacao"]] = db.relationship(  # type: ignore[name-defined]
        "Notificacao", back_populates="ocorrencia", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Ocorrencia id={self.id} origem={self.origem!r} "
            f"status={self.status!r} empresa_id={self.empresa_id}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "empresa_id": self.empresa_id,
            "unidade_id": self.unidade_id,
            "origem": self.origem,
            "tipo": self.tipo,
            "prioridade": self.prioridade,
            "status": self.status,
            "responsavel_id": self.responsavel_id,
            "aberto_em": self.aberto_em.isoformat() if self.aberto_em else None,
            "tratado_em": self.tratado_em.isoformat() if self.tratado_em else None,
        }
