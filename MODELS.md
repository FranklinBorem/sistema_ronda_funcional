"""
models/__init__.py

Exporta todos os models para registro no SQLAlchemy.
"""
from .alerta import Alerta
from .mensagem import Mensagem, StatusSistema
from .monitor import Monitor
from .monitoring import CameraStatusLog, MonitorEvent
from .nvr import Nvr, NvrPreset
from .nvr_status_log import NvrStatusLog
from .ronda import Ronda


__all__ = [
    "Alerta",
    "CameraStatusLog",
    "Mensagem",
    "Monitor",
    "MonitorEvent",
    "Nvr",
    "NvrPreset",
    "NvrStatusLog",
    "Ronda",
    "StatusSistema",
]

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
    PENDENTE       = "pendente"
    TRATADO        = "tratado"
    DETECCAO_FALSA = "deteccao_falsa"


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
    ) -> None:
        """Registra tratativa e atualiza status."""
        self.status = novo_status.value
        self.tratativa = tratativa
        self.responsavel = responsavel
        if novo_status in (StatusAlerta.TRATADO, StatusAlerta.DETECCAO_FALSA):
            self.tratado_em = datetime.utcnow()

    def reabrir(self) -> None:
        """Volta o alerta para pendente, limpando a tratativa."""
        self.status = StatusAlerta.PENDENTE.value
        self.tratativa = None
        self.responsavel = None
        self.tratado_em = None

    @property
    def is_pendente(self) -> bool:
        return self.status == StatusAlerta.PENDENTE.value

    def __repr__(self) -> str:
        return (
            f"<Alerta id={self.id} nvr={self.nvr_id!r} "
            f"local={self.local_preset!r} pessoas={self.pessoas} status={self.status!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "ronda_id":     self.ronda_id,
            "nvr_id":       self.nvr_id,
            "nvr_nome":     self.nvr_nome,
            "ufv":          self.ufv or "—",
            "local_preset": self.local_preset,
            "pessoas":      self.pessoas,
            "imagem_path":  self.imagem_path,
            "detectado_em": self.detectado_em.isoformat() if self.detectado_em else None,
            "status":       self.status,
            "tratativa":    self.tratativa or "",
            "responsavel":  self.responsavel or "",
            "tratado_em":   self.tratado_em.isoformat() if self.tratado_em else None,
        }

"""
models/mensagem.py — Mensagens WhatsApp e status do conector Node.js.

Substitui as tabelas `mensagens` e `status_sistema` do mensagens.db.
Consolidado no banco principal (PostgreSQL) para eliminar o segundo
arquivo SQLite separado.
"""

from __future__ import annotations

from datetime import datetime

from extensions import db


class Mensagem(db.Model):
    __tablename__ = "mensagens"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)

    grupo: db.Mapped[str | None] = db.mapped_column(
        db.String(200), nullable=True, index=True
    )
    autor: db.Mapped[str | None] = db.mapped_column(db.String(200), nullable=True)

    # ISO 8601 vindo do Node.js — armazenado como DateTime no Postgres
    data: db.Mapped[datetime | None] = db.mapped_column(
        db.DateTime, nullable=True, index=True
    )

    tipo: db.Mapped[str | None] = db.mapped_column(
        db.String(30), nullable=True          # "chat", "image", "audio", etc.
    )
    conteudo: db.Mapped[str | None] = db.mapped_column(db.Text, nullable=True)

    # Classificação de alerta feita pelo sistema — ex: "urgente", ""
    alerta: db.Mapped[str] = db.mapped_column(
        db.String(60), nullable=False, default=""
    )

    def __repr__(self) -> str:
        return (
            f"<Mensagem id={self.id} grupo={self.grupo!r} "
            f"autor={self.autor!r} tipo={self.tipo!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id":       self.id,
            "grupo":    self.grupo,
            "autor":    self.autor,
            "data":     self.data.isoformat() if self.data else None,
            "tipo":     self.tipo,
            "conteudo": self.conteudo,
            "alerta":   self.alerta,
        }


class StatusSistema(db.Model):
    """
    Linha única que registra o último heartbeat recebido do conector WhatsApp.
    Sempre id=1 — use StatusSistema.get() para acessar.
    """
    __tablename__ = "status_sistema"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    ultima_verificacao_sistema: db.Mapped[datetime | None] = db.mapped_column(
        db.DateTime, nullable=True
    )

    @classmethod
    def get(cls) -> "StatusSistema":
        """
        Retorna a linha de status (id=1), criando-a se não existir.
        Deve ser chamado dentro de um contexto de aplicação Flask.
        """
        instance = db.session.get(cls, 1)
        if instance is None:
            instance = cls(id=1, ultima_verificacao_sistema=datetime.utcnow())
            db.session.add(instance)
            db.session.commit()
        return instance

    def atualizar(self, timestamp: datetime | None = None) -> None:
        self.ultima_verificacao_sistema = timestamp or datetime.utcnow()

    def __repr__(self) -> str:
        return f"<StatusSistema ultima={self.ultima_verificacao_sistema!r}>"

"""
models/monitor.py — Usuários do sistema (monitores de segurança).

Mapeamento da tabela `monitores` para SQLAlchemy ORM.
"""

from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class Monitor(db.Model):
    __tablename__ = "monitores"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    nome: db.Mapped[str] = db.mapped_column(db.String(120), nullable=False)
    usuario: db.Mapped[str] = db.mapped_column(
        db.String(60), nullable=False, unique=True, index=True
    )
    senha: db.Mapped[str] = db.mapped_column(db.String(256), nullable=False)
    turno: db.Mapped[str] = db.mapped_column(db.String(60), nullable=False)

    # ── Relacionamentos ────────────────────────────────────────────────────
    rondas: db.Mapped[list["Ronda"]] = db.relationship(  # type: ignore[name-defined]
        "Ronda", back_populates="monitor", lazy="dynamic"
    )

    # ── Métodos de senha ───────────────────────────────────────────────────

    def set_senha(self, senha_plain: str) -> None:
        """Gera hash e armazena. Nunca armazene senha em texto plano."""
        self.senha = generate_password_hash(senha_plain)

    def verificar_senha(self, senha_plain: str) -> bool:
        """Retorna True se a senha bate com o hash armazenado."""
        return check_password_hash(self.senha, senha_plain)

    # ── Representação ──────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"<Monitor id={self.id} usuario={self.usuario!r} turno={self.turno!r}>"

    def to_dict(self) -> dict:
        return {
            "id":     self.id,
            "nome":   self.nome,
            "usuario": self.usuario,
            "turno":  self.turno,
        }

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
