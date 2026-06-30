"""
models/nvr.py — Cadastro de NVRs / speed domes e seus presets.

Tabelas:
    nvrs         — configuracao de cada speed dome/NVR
    nvr_presets  — presets numerados de cada NVR (1:Portao, 2:Skid, ...)
"""

from __future__ import annotations

from extensions import db


# ── Models ──────────────────────────────────────────────────────────────

class Nvr(db.Model):
    """
    Configuracao de um NVR / speed dome.
    Substitui o antigo cadastro via nvr_speed_domes.csv/xlsx.

    IMPORTANTE: a tabela real ja existente no banco usa `id` (integer,
    autoincremento) como chave tecnica e `nvr_id` (string) como o
    identificador de negocio (ex.: "bes2_dome_1", "altair_dome_1"). E o
    `nvr_id` que e referenciado pela FK em nvr_presets, nao o `id`.
    """
    __tablename__ = "nvrs"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    nvr_id: db.Mapped[str] = db.mapped_column(
        db.String(120), nullable=False, unique=True, index=True
    )
    site: db.Mapped[str | None] = db.mapped_column(db.String(200), nullable=True)
    nome: db.Mapped[str] = db.mapped_column(db.String(200), nullable=False)
    ip: db.Mapped[str] = db.mapped_column(db.String(60), nullable=False)
    usuario: db.Mapped[str] = db.mapped_column(db.String(60), nullable=False, default="admin")
    senha: db.Mapped[str] = db.mapped_column(db.String(200), nullable=False, default="")

    # ── PTZ / Snapshot ───────────────────────────────────────────────────
    # Canal usado para comandos PTZ (goto preset). Hikvision tipicamente
    # usa o numero do canal de video correspondente a essa speed dome.
    ptz_channel: db.Mapped[int] = db.mapped_column(
        db.Integer, nullable=False, default=1
    )
    # Canal usado para capturar o snapshot JPEG (Streaming/channels/{N}/picture).
    # Em NVRs Hikvision, geralmente e "{canal}01" (ex.: canal 5 -> "501").
    snapshot_channel: db.Mapped[str] = db.mapped_column(
        db.String(20), nullable=False, default="501"
    )

    tempo_espera: db.Mapped[int] = db.mapped_column(db.Integer, nullable=False, default=5)
    timeout: db.Mapped[int] = db.mapped_column(db.Integer, nullable=False, default=10)

    ativo: db.Mapped[bool] = db.mapped_column(db.Boolean, nullable=False, default=True)

    # ── Relacionamentos ────────────────────────────────────────────────
    # A FK em nvr_presets aponta para nvrs.nvr_id (string de negocio),
    # nao para nvrs.id (PK tecnica) — por isso o primaryjoin explicito.
    presets: db.Mapped[list["NvrPreset"]] = db.relationship(
        "NvrPreset", back_populates="nvr", cascade="all, delete-orphan",
        order_by="NvrPreset.numero",
        primaryjoin="Nvr.nvr_id == NvrPreset.nvr_id",
    )

    # ── Representação ─────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"<Nvr nvr_id={self.nvr_id!r} nome={self.nome!r} ip={self.ip!r} "
            f"ptz_channel={self.ptz_channel} ativo={self.ativo}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nvr_id": self.nvr_id,
            "site": self.site,
            "nome": self.nome,
            "ip": self.ip,
            "usuario": self.usuario,
            "ptz_channel": self.ptz_channel,
            "snapshot_channel": self.snapshot_channel,
            "presets": {p.numero: p.nome for p in self.presets},
            "tempo_espera": self.tempo_espera,
            "timeout": self.timeout,
            "ativo": self.ativo,
        }


class NvrPreset(db.Model):
    """
    Preset numerado de um NVR (posicao da speed dome).
    Ex.: numero=1, nome="Portao principal".
    """
    __tablename__ = "nvr_presets"
    __table_args__ = (
        db.UniqueConstraint("nvr_id", "numero", name="uq_nvr_presets_nvr_numero"),
    )

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    nvr_id: db.Mapped[str] = db.mapped_column(
        db.String(120), db.ForeignKey("nvrs.nvr_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    numero: db.Mapped[int] = db.mapped_column(db.Integer, nullable=False)
    nome: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False)

    # ── Relacionamento ─────────────────────────────────────────────────
    nvr: db.Mapped["Nvr"] = db.relationship(
        "Nvr", back_populates="presets",
        primaryjoin="NvrPreset.nvr_id == Nvr.nvr_id",
    )

    def __repr__(self) -> str:
        return f"<NvrPreset nvr_id={self.nvr_id!r} numero={self.numero} nome={self.nome!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nvr_id": self.nvr_id,
            "numero": self.numero,
            "nome": self.nome,
        }
