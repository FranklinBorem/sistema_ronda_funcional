"""
models/nvr_status_log.py — Histórico de status de NVRs (Conferência de Câmeras).

Cada execução do poller (ConferenceManager.poll_all) grava uma linha por NVR.
Permite reconstruir quando um NVR ficou inacessível/em atenção e por quanto tempo.
"""

from __future__ import annotations

from datetime import datetime

from extensions import db


class NvrStatusLog(db.Model):
    __tablename__ = "nvr_status_log"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)

    nvr_id: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False, index=True)
    nvr_nome: db.Mapped[str] = db.mapped_column(db.String(200), nullable=False)

    timestamp: db.Mapped[datetime] = db.mapped_column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    health: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False)  # OK | ATENÇÃO | INACESSÍVEL
    reachable: db.Mapped[bool] = db.mapped_column(db.Boolean, nullable=False, default=False)

    cameras_total: db.Mapped[int] = db.mapped_column(db.Integer, nullable=False, default=0)
    cameras_online: db.Mapped[int] = db.mapped_column(db.Integer, nullable=False, default=0)
    cameras_offline: db.Mapped[int] = db.mapped_column(db.Integer, nullable=False, default=0)

    erro: db.Mapped[str | None] = db.mapped_column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nvr_id": self.nvr_id,
            "nvr_nome": self.nvr_nome,
            "timestamp": self.timestamp.isoformat(),
            "health": self.health,
            "reachable": self.reachable,
            "cameras_total": self.cameras_total,
            "cameras_online": self.cameras_online,
            "cameras_offline": self.cameras_offline,
            "erro": self.erro,
        }
