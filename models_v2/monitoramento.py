"""
models_v2/monitoramento.py — NvrStatusLog e CameraStatusLog: log bruto
de disponibilidade, um registro por ciclo de polling ISAPI (schema
novo).

LACUNA ENCONTRADA E CORRIGIDA NA FASE D (não fazia parte do modelo
original da Fase -1): docs/database/modelo-banco.md menciona
`nvr_status_log`/`camera_status_log` como se já existissem no schema
novo, mas eram um resquício do schema antigo nunca de fato modelado
aqui — só `Ocorrencia` (eventos de falha, abertura/fechamento) tinha
sido criada. Faltava o log granular por ciclo de verificação (ex.:
"às 14:32:05, câmera X respondeu em 180ms"), que é o que alimenta o
dashboard de disponibilidade/SLA, não só o registro de quando uma
falha começou e terminou.
"""

from __future__ import annotations

from datetime import datetime, timezone

from extensions import db


class NvrStatusLog(db.Model):
    __tablename__ = "nvr_status_log"

    id: db.Mapped[int] = db.mapped_column(db.BigInteger, primary_key=True)
    nvr_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("nvrs.id"), nullable=False
    )
    online: db.Mapped[bool] = db.mapped_column(db.Boolean, nullable=False)
    latencia_ms: db.Mapped[int | None] = db.mapped_column(db.Integer, nullable=True)
    detalhes: db.Mapped[dict | None] = db.mapped_column(db.JSON, nullable=True)
    timestamp: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_nvr_status_log_nvr_timestamp", "nvr_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<NvrStatusLog nvr_id={self.nvr_id} online={self.online} timestamp={self.timestamp}>"


class CameraStatusLog(db.Model):
    __tablename__ = "camera_status_log"

    id: db.Mapped[int] = db.mapped_column(db.BigInteger, primary_key=True)
    camera_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("cameras.id"), nullable=False
    )
    online: db.Mapped[bool] = db.mapped_column(db.Boolean, nullable=False)
    detalhes: db.Mapped[dict | None] = db.mapped_column(db.JSON, nullable=True)
    timestamp: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_camera_status_log_camera_timestamp", "camera_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<CameraStatusLog camera_id={self.camera_id} online={self.online} timestamp={self.timestamp}>"
