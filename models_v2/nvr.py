"""
models/v2/nvr.py — Nvr (grupo/site organizacional de câmeras, geralmente
também um dispositivo físico), Camera (com modo_conexao: via_nvr ou
ip_direto — ver docs/database/modelo-banco.md) e Preset.

Unifica models/nvr.py:Nvr e models/nvr_monitorado.py:NvrMonitorado do
schema antigo (Decisão 1 de docs/decisions/decisoes-pendentes.md,
resolvida — sem dado legado a proteger após a perda do banco de
produção).
"""

from __future__ import annotations

from extensions import db

TIPOS_CAMERA_VALIDOS = ("bullet", "dome", "dome_interna", "ptz", "generica")

# Sugestão de capacidades por tipo, aplicada no cadastro e editável depois.
CAPACIDADES_PADRAO_POR_TIPO = {
    "ptz": {"ptz": True, "presets": True, "captura": True, "stream": True},
    "bullet": {"ptz": False, "presets": False, "captura": True, "stream": True},
    "dome": {"ptz": False, "presets": False, "captura": True, "stream": True},
    "dome_interna": {"ptz": False, "presets": False, "captura": True, "stream": True},
    "generica": {"ptz": False, "presets": False, "captura": True, "stream": True},
}


class Nvr(db.Model):
    __tablename__ = "nvrs"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    unidade_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("unidades.id"), nullable=False
    )
    nome: db.Mapped[str] = db.mapped_column(db.String(150), nullable=False)
    fabricante: db.Mapped[str] = db.mapped_column(
        db.String(50), nullable=False, default="hikvision"
    )
    modelo: db.Mapped[str | None] = db.mapped_column(db.String(80), nullable=True)
    # nullable: um Nvr pode existir só como agrupador organizacional de
    # câmeras avulsas (ip_direto), sem ser ele mesmo um dispositivo
    # consultável via ISAPI.
    endereco_ip: db.Mapped[str | None] = db.mapped_column(db.String(50), nullable=True)
    porta: db.Mapped[int | None] = db.mapped_column(db.Integer, nullable=True, default=80)
    usuario_acesso: db.Mapped[str | None] = db.mapped_column(db.String(80), nullable=True)
    credencial_ref: db.Mapped[str | None] = db.mapped_column(db.String(255), nullable=True)
    status: db.Mapped[str] = db.mapped_column(
        db.String(20), nullable=False, default="ativo"
    )

    __table_args__ = (
        db.CheckConstraint("status IN ('ativo','inativo')", name="ck_nvrs_status"),
        db.Index("ix_nvrs_unidade_id", "unidade_id"),
        db.Index("ix_nvrs_endereco_ip", "endereco_ip"),
    )

    # ── Relacionamentos ─────────────────────────────────────────────────
    unidade: db.Mapped["Unidade"] = db.relationship(  # type: ignore[name-defined]
        "Unidade", back_populates="nvrs"
    )
    cameras: db.Mapped[list["Camera"]] = db.relationship(
        "Camera", back_populates="nvr", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Nvr id={self.id} nome={self.nome!r} unidade_id={self.unidade_id}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "unidade_id": self.unidade_id,
            "nome": self.nome,
            "fabricante": self.fabricante,
            "modelo": self.modelo,
            "endereco_ip": self.endereco_ip,
            "status": self.status,
            "cameras": [c.to_dict() for c in self.cameras],
        }


class Camera(db.Model):
    """
    Toda câmera pertence a um `nvr_id` (o grupo/site) — nunca existe
    câmera sem NVR, mesmo quando o cadastro é feito câmera por câmera.

    `modo_conexao`:
      - "via_nvr":    conecta através de um canal do NVR físico pai
                      (nvr.endereco_ip + este `canal`)
      - "ip_direto":  câmera avulsa (dome/fixa) com IP próprio,
                      organizada sob o mesmo grupo/site
    """
    __tablename__ = "cameras"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    nvr_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("nvrs.id"), nullable=False
    )
    modo_conexao: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False)
    canal: db.Mapped[int | None] = db.mapped_column(db.Integer, nullable=True)
    endereco_ip: db.Mapped[str | None] = db.mapped_column(db.String(50), nullable=True)
    porta: db.Mapped[int | None] = db.mapped_column(db.Integer, nullable=True)
    usuario_acesso: db.Mapped[str | None] = db.mapped_column(db.String(80), nullable=True)
    credencial_ref: db.Mapped[str | None] = db.mapped_column(db.String(255), nullable=True)
    tipo: db.Mapped[str] = db.mapped_column(db.String(20), nullable=False)
    nome: db.Mapped[str | None] = db.mapped_column(db.String(100), nullable=True)
    capacidades: db.Mapped[dict] = db.mapped_column(
        db.JSON, nullable=False, default=dict
    )

    __table_args__ = (
        db.CheckConstraint(
            "modo_conexao IN ('via_nvr','ip_direto')", name="ck_cameras_modo_conexao"
        ),
        db.CheckConstraint(
            "(modo_conexao = 'via_nvr' AND canal IS NOT NULL) OR "
            "(modo_conexao = 'ip_direto' AND endereco_ip IS NOT NULL)",
            name="ck_cameras_conexao_valida",
        ),
        db.CheckConstraint(
            "tipo IN ('bullet','dome','dome_interna','ptz','generica')",
            name="ck_cameras_tipo",
        ),
        db.Index(
            "uq_cameras_nvr_canal", "nvr_id", "canal", unique=True,
            postgresql_where=db.text("modo_conexao = 'via_nvr'"),
        ),
        db.Index(
            "uq_cameras_nvr_ip", "nvr_id", "endereco_ip", unique=True,
            postgresql_where=db.text("modo_conexao = 'ip_direto'"),
        ),
    )

    # ── Relacionamentos ─────────────────────────────────────────────────
    nvr: db.Mapped["Nvr"] = db.relationship("Nvr", back_populates="cameras")
    presets: db.Mapped[list["Preset"]] = db.relationship(
        "Preset", back_populates="camera", cascade="all, delete-orphan",
        order_by="Preset.numero",
    )
    regras_deteccao: db.Mapped[list["RegraDeteccao"]] = db.relationship(  # type: ignore[name-defined]
        "RegraDeteccao", back_populates="camera", cascade="all, delete-orphan"
    )

    def aplicar_capacidades_padrao(self) -> None:
        """Sugere capacidades a partir do `tipo` — chamar no cadastro; editável depois."""
        self.capacidades = dict(CAPACIDADES_PADRAO_POR_TIPO.get(self.tipo, {}))

    def __repr__(self) -> str:
        alvo = f"canal={self.canal}" if self.modo_conexao == "via_nvr" else f"ip={self.endereco_ip}"
        return f"<Camera id={self.id} nvr_id={self.nvr_id} modo={self.modo_conexao} {alvo}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nvr_id": self.nvr_id,
            "modo_conexao": self.modo_conexao,
            "canal": self.canal,
            "endereco_ip": self.endereco_ip,
            "tipo": self.tipo,
            "nome": self.nome,
            "capacidades": self.capacidades,
        }


class Preset(db.Model):
    __tablename__ = "presets"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    camera_id: db.Mapped[int] = db.mapped_column(
        db.Integer, db.ForeignKey("cameras.id"), nullable=False
    )
    numero: db.Mapped[int] = db.mapped_column(db.Integer, nullable=False)
    descricao: db.Mapped[str | None] = db.mapped_column(db.String(150), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("camera_id", "numero", name="uq_presets_camera_numero"),
    )

    camera: db.Mapped["Camera"] = db.relationship("Camera", back_populates="presets")

    def __repr__(self) -> str:
        return f"<Preset id={self.id} camera_id={self.camera_id} numero={self.numero}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "numero": self.numero,
            "descricao": self.descricao,
        }
