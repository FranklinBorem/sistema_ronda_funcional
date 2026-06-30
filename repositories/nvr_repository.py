"""
repositories/nvr_repository.py — CRUD para Nvr e NvrPreset.

Substitui nvr_db.py (SQLite puro).
Segue o padrão do projeto: injeção de session opcional,
fallback para db.session quando não fornecida.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from extensions import db
from models.nvr import Nvr, NvrPreset


class NvrRepository:
    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session or db.session

    # ── Consultas ──────────────────────────────────────────────────────────

    def listar(self, apenas_ativos: bool = False) -> list[Nvr]:
        q = self.session.query(Nvr)
        if apenas_ativos:
            q = q.filter(Nvr.ativo.is_(True))
        return q.order_by(Nvr.nome).all()

    def buscar_por_nvr_id(self, nvr_id: str) -> Nvr | None:
        return self.session.query(Nvr).filter_by(nvr_id=nvr_id).first()

    # ── Criação ────────────────────────────────────────────────────────────

    def criar(
        self,
        nvr_id: str,
        nome: str,
        ip: str,
        usuario: str,
        senha: str,
        ptz_channel: int,
        snapshot_channel: str,
        tempo_espera: int,
        timeout: int,
        ativo: bool,
        presets: dict[int, str],   # {numero: nome}
        site: str = "",
    ) -> Nvr:
        """Cria um novo NVR com seus presets. Lança ValueError se nvr_id já existir."""
        if self.buscar_por_nvr_id(nvr_id):
            raise ValueError(f"PTZ com ID '{nvr_id}' já existe.")

        nvr = Nvr(
            nvr_id=nvr_id,
            nome=nome,
            ip=ip,
            usuario=usuario,
            senha=senha,
            site=site or None,
            ptz_channel=ptz_channel,
            snapshot_channel=snapshot_channel,
            tempo_espera=tempo_espera,
            timeout=timeout,
            ativo=ativo,
        )
        self.session.add(nvr)
        self.session.flush()  # garante nvr.nvr_id disponível para os presets

        self._sincronizar_presets(nvr, presets)
        self.session.commit()
        return nvr

    # ── Atualização ────────────────────────────────────────────────────────

    def atualizar(
        self,
        nvr_id: str,
        nome: str,
        ip: str,
        usuario: str,
        senha: str | None,         # None = manter senha atual
        ptz_channel: int,
        snapshot_channel: str,
        tempo_espera: int,
        timeout: int,
        ativo: bool,
        presets: dict[int, str],
        site: str = "",
    ) -> Nvr:
        nvr = self.buscar_por_nvr_id(nvr_id)
        if not nvr:
            raise ValueError(f"PTZ '{nvr_id}' não encontrada.")

        nvr.nome             = nome
        nvr.ip               = ip
        nvr.usuario          = usuario
        nvr.site             = site or None
        nvr.ptz_channel      = ptz_channel
        nvr.snapshot_channel = snapshot_channel
        nvr.tempo_espera     = tempo_espera
        nvr.timeout          = timeout
        nvr.ativo            = ativo

        if senha:
            nvr.senha = senha

        self._sincronizar_presets(nvr, presets)
        self.session.commit()
        return nvr

    # ── Toggle ativo ───────────────────────────────────────────────────────

    def toggle_ativo(self, nvr_id: str) -> Nvr:
        nvr = self.buscar_por_nvr_id(nvr_id)
        if not nvr:
            raise ValueError(f"PTZ '{nvr_id}' não encontrada.")
        nvr.ativo = not nvr.ativo
        self.session.commit()
        return nvr

    # ── Exclusão ───────────────────────────────────────────────────────────

    def excluir(self, nvr_id: str) -> None:
        nvr = self.buscar_por_nvr_id(nvr_id)
        if nvr:
            self.session.delete(nvr)  # cascade deleta os presets
            self.session.commit()

    # ── Helpers internos ───────────────────────────────────────────────────

    def _sincronizar_presets(self, nvr: Nvr, presets: dict[int, str]) -> None:
        """Substitui todos os presets do NVR pelos fornecidos."""
        # Remove presets existentes
        for p in list(nvr.presets):
            self.session.delete(p)
        self.session.flush()

        # Insere os novos
        for numero, nome in presets.items():
            self.session.add(NvrPreset(nvr_id=nvr.nvr_id, numero=numero, nome=nome))
