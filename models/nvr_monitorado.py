"""
models/nvr_monitorado.py — Grupo Ronda · Conferência de Câmeras

Tabela separada para NVRs monitorados pelo módulo de conferência.
Não mistura com o modelo Nvr (PTZ individuais).
"""

from __future__ import annotations

from datetime import datetime

from extensions import db  # ajuste para o seu import de db, ex: from app import db


class NvrMonitorado(db.Model):
    __tablename__ = "nvr_monitorado"

    id        = db.Column(db.Integer, primary_key=True)
    nvr_id    = db.Column(db.String(80), unique=True, nullable=False)   # slug único, ex: "ufv01_nvr"
    nome      = db.Column(db.String(120), nullable=False)               # "UFV 01 – NVR Principal"
    site      = db.Column(db.String(120), default="")                   # "Altair – SP"
    ip        = db.Column(db.String(45),  nullable=False)               # IPv4 ou IPv6
    porta     = db.Column(db.Integer,     default=80)                   # 80 HTTP / 443 HTTPS
    use_https = db.Column(db.Boolean,     default=False)
    usuario   = db.Column(db.String(80),  default="admin")
    senha     = db.Column(db.String(120), nullable=False)
    ativo     = db.Column(db.Boolean,     default=True)
    criado_em = db.Column(db.DateTime,    default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<NvrMonitorado {self.nvr_id} {self.ip}>"

    def to_dict(self) -> dict:
        return {
            "id":        self.id,
            "nvr_id":   self.nvr_id,
            "nome":     self.nome,
            "site":     self.site,
            "ip":       self.ip,
            "porta":    self.porta,
            "use_https": self.use_https,
            "usuario":  self.usuario,
            "ativo":    self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
