"""
models/alerta.py — Alertas gerados pelo motor YOLO durante as rondas.

Substitui a tabela `alertas` do alarmes_schema.py com tipagem completa
e enum para status.
"""

from __future__ import annotations

import enum
from datetime import datetime

from extensions import db


class StatusAlerta(str, enum.Enum):
    PENDENTE = "pendente"
    TRATADO  = "tratado"


class MotivoTratamento(str, enum.Enum):
    """Subcategoria de um alerta TRATADO — substitui o antigo status
    'Detecção Falsa', que agora é um motivo dentro de 'Tratado'."""
    CONFIRMADO     = "confirmado"
    FALSO_POSITIVO = "falso_positivo"


class Alerta(db.Model):
    __tablename__ = "alertas"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)

    # ── Origem ─────────────────────────────────────────────────────────────
    ronda_id: db.Mapped[int | None] = db.mapped_column(
        db.Integer,
        db.ForeignKey("rondas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nvr_id: db.Mapped[str] = db.mapped_column(db.String(60), nullable=False, index=True)
    nvr_nome: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False)

    # UFV / site ao qual o NVR pertence — preenchido a partir de NVRConfig.site
    ufv: db.Mapped[str | None] = db.mapped_column(
        db.String(120), nullable=True, index=True
    )

    # ── Detecção ───────────────────────────────────────────────────────────
    local_preset: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False)
    pessoas: db.Mapped[int] = db.mapped_column(db.Integer, default=0, nullable=False)

    # Caminho relativo a partir de /relatorios — ex: "loop_.../nvr_01/imagens/Portaria_deteccao.jpg"
    imagem_path: db.Mapped[str | None] = db.mapped_column(db.Text, nullable=True)

    detectado_em: db.Mapped[datetime] = db.mapped_column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    # ── Tratativa ──────────────────────────────────────────────────────────
    status: db.Mapped[str] = db.mapped_column(
        db.String(30),
        nullable=False,
        default=StatusAlerta.PENDENTE.value,
        index=True,
    )
    # Só preenchido quando status == TRATADO. Substitui o antigo status
    # irmão 'deteccao_falsa' — agora é uma subcategoria de 'tratado'.
    motivo_tratamento: db.Mapped[str | None] = db.mapped_column(
        db.String(30), nullable=True, index=True
    )
    tratativa: db.Mapped[str | None] = db.mapped_column(db.Text, nullable=True)
    responsavel: db.Mapped[str | None] = db.mapped_column(db.String(120), nullable=True)
    tratado_em: db.Mapped[datetime | None] = db.mapped_column(db.DateTime, nullable=True)

    # ── Relacionamento ─────────────────────────────────────────────────────
    ronda: db.Mapped["Ronda"] = db.relationship(  # type: ignore[name-defined]
        "Ronda", back_populates="alertas"
    )

    # ── Helpers ────────────────────────────────────────────────────────────

    def tratar(
        self,
        novo_status: StatusAlerta,
        tratativa: str,
        responsavel: str,
        motivo: MotivoTratamento | None = None,
    ) -> None:
        """Registra tratativa e atualiza status.

        `motivo` só se aplica quando novo_status == TRATADO. Se não vier
        explícito, assume CONFIRMADO (comportamento antigo de "Tratado"
        sem subcategoria).
        """
        self.status = novo_status.value
        self.tratativa = tratativa
        self.responsavel = responsavel
        if novo_status == StatusAlerta.TRATADO:
            self.motivo_tratamento = (motivo or MotivoTratamento.CONFIRMADO).value
            self.tratado_em = datetime.utcnow()
        else:
            self.motivo_tratamento = None
            self.tratado_em = None

    def reabrir(self) -> None:
        """Volta o alerta para pendente, limpando a tratativa."""
        self.status = StatusAlerta.PENDENTE.value
        self.motivo_tratamento = None
        self.tratativa = None
        self.responsavel = None
        self.tratado_em = None

    @property
    def is_pendente(self) -> bool:
        return self.status == StatusAlerta.PENDENTE.value

    @property
    def is_falso_positivo(self) -> bool:
        return (
            self.status == StatusAlerta.TRATADO.value
            and self.motivo_tratamento == MotivoTratamento.FALSO_POSITIVO.value
        )

    def __repr__(self) -> str:
        return (
            f"<Alerta id={self.id} nvr={self.nvr_id!r} "
            f"local={self.local_preset!r} pessoas={self.pessoas} "
            f"status={self.status!r} motivo={self.motivo_tratamento!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id":                self.id,
            "ronda_id":          self.ronda_id,
            "nvr_id":            self.nvr_id,
            "nvr_nome":          self.nvr_nome,
            "ufv":               self.ufv or "—",
            "local_preset":      self.local_preset,
            "pessoas":           self.pessoas,
            "imagem_path":       self.imagem_path,
            "detectado_em":      self.detectado_em.isoformat() if self.detectado_em else None,
            "status":            self.status,
            "motivo_tratamento": self.motivo_tratamento,
            "tratativa":         self.tratativa or "",
            "responsavel":       self.responsavel or "",
            "tratado_em":        self.tratado_em.isoformat() if self.tratado_em else None,
        }
