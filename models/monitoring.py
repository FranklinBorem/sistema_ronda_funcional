"""
models/monitoring.py — Camada de monitoramento estilo Zabbix (eventos + séries por câmera).

Não tem FK para a tabela `nvrs` propositalmente: o monitoramento é uma camada
aditiva e independente do cadastro operacional de PTZ/rondas. Se um NVR for
removido do cadastro, o histórico de monitoramento permanece intacto.
"""

from __future__ import annotations

from datetime import datetime

from extensions import db


class CameraStatusLog(db.Model):
    """Série temporal por canal de câmera (equivalente a um 'item' do Zabbix)."""
    __tablename__ = "camera_status_log"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)

    nvr_id: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False, index=True)
    channel_id: db.Mapped[int] = db.mapped_column(db.Integer, nullable=False, index=True)
    channel_name: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False, default="")

    timestamp: db.Mapped[datetime] = db.mapped_column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    online: db.Mapped[bool] = db.mapped_column(db.Boolean, nullable=False, default=False)
    signal_ok: db.Mapped[bool] = db.mapped_column(db.Boolean, nullable=False, default=False)
    recording: db.Mapped[bool] = db.mapped_column(db.Boolean, nullable=False, default=False)
    bit_rate_kbps: db.Mapped[int] = db.mapped_column(db.Integer, nullable=False, default=0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nvr_id": self.nvr_id,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "timestamp": self.timestamp.isoformat(),
            "online": self.online,
            "signal_ok": self.signal_ok,
            "recording": self.recording,
            "bit_rate_kbps": self.bit_rate_kbps,
        }


class MonitorEvent(db.Model):
    """
    Evento de monitoramento (equivalente a 'Problem' do Zabbix).

    Um evento é ABERTO quando uma condição de falha é detectada, e FECHADO
    (resolvido) quando a condição deixa de existir. Enquanto aberto,
    resolved_em é None — isso permite calcular MTTR e uptime% por alvo.
    """
    __tablename__ = "monitor_event"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)

    # Alvo do evento: "nvr" ou "camera"
    alvo_tipo: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False, index=True)
    nvr_id: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False, index=True)
    channel_id: db.Mapped[int | None] = db.mapped_column(db.Integer, nullable=True)

    nome_exibicao: db.Mapped[str] = db.mapped_column(db.String(200), nullable=False, default="")

    # baixa | media | alta | critica  (equivalente à severidade do Zabbix)
    severidade: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False, default="media")

    chave_problema: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False)
    # Ex.: "nvr_inacessivel", "nvr_atencao", "camera_offline", "camera_sem_sinal"

    mensagem: db.Mapped[str] = db.mapped_column(db.Text, nullable=False, default="")

    aberto_em: db.Mapped[datetime] = db.mapped_column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    resolvido_em: db.Mapped[datetime | None] = db.mapped_column(db.DateTime, nullable=True)

    notificado: db.Mapped[bool] = db.mapped_column(db.Boolean, nullable=False, default=False)

    @property
    def ativo(self) -> bool:
        return self.resolvido_em is None

    @property
    def duracao_minutos(self) -> float | None:
        fim = self.resolvido_em or datetime.utcnow()
        return round((fim - self.aberto_em).total_seconds() / 60, 1)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "alvo_tipo": self.alvo_tipo,
            "nvr_id": self.nvr_id,
            "channel_id": self.channel_id,
            "nome_exibicao": self.nome_exibicao,
            "severidade": self.severidade,
            "chave_problema": self.chave_problema,
            "mensagem": self.mensagem,
            "aberto_em": self.aberto_em.isoformat(),
            "resolvido_em": self.resolvido_em.isoformat() if self.resolvido_em else None,
            "ativo": self.ativo,
            "duracao_minutos": self.duracao_minutos,
        }
