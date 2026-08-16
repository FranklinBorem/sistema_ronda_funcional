"""
repositories/nvr_repository.py — CRUD único para Nvr e NvrPreset.

Fonte de dados única para todo o sistema (PTZ, Conferência, polling ISAPI,
relatórios, WhatsApp, etc.). Segue o padrão do projeto: injeção de session
opcional, fallback para db.session quando não fornecida.
"""

from __future__ import annotations

import csv
import io

from sqlalchemy.orm import Session

from extensions import db
from models.nvr import Nvr, NvrPreset

_TRUTHY = {"1", "true", "sim", "yes", "s", "y"}


def _parse_bool_csv(val: str) -> bool:
    return str(val).strip().lower() in _TRUTHY


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
        ptz_channel: int = 1,
        snapshot_channel: str = "501",
        tempo_espera: int = 5,
        timeout: int = 10,
        ativo: bool = True,
        presets: dict[int, str] | None = None,
        site: str = "",
        porta: int = 80,
        use_https: bool = False,
    ) -> Nvr:
        """Cria um novo NVR com seus presets. Lança ValueError se nvr_id já existir."""
        if self.buscar_por_nvr_id(nvr_id):
            raise ValueError(f"NVR com ID '{nvr_id}' já existe.")

        nvr = Nvr(
            nvr_id=nvr_id,
            nome=nome,
            ip=ip,
            usuario=usuario,
            senha=senha,
            site=site or None,
            porta=porta,
            use_https=use_https,
            ptz_channel=ptz_channel,
            snapshot_channel=snapshot_channel,
            tempo_espera=tempo_espera,
            timeout=timeout,
            ativo=ativo,
        )
        self.session.add(nvr)
        self.session.flush()  # garante nvr.nvr_id disponível para os presets

        self._sincronizar_presets(nvr, presets or {})
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
        porta: int = 80,
        use_https: bool = False,
    ) -> Nvr:
        nvr = self.buscar_por_nvr_id(nvr_id)
        if not nvr:
            raise ValueError(f"NVR '{nvr_id}' não encontrado.")

        nvr.nome             = nome
        nvr.ip               = ip
        nvr.usuario          = usuario
        nvr.site             = site or None
        nvr.porta            = porta
        nvr.use_https        = use_https
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
            raise ValueError(f"NVR '{nvr_id}' não encontrado.")
        nvr.ativo = not nvr.ativo
        self.session.commit()
        return nvr

    # ── Exclusão ───────────────────────────────────────────────────────────

    def excluir(self, nvr_id: str) -> None:
        nvr = self.buscar_por_nvr_id(nvr_id)
        if nvr:
            self.session.delete(nvr)  # cascade deleta os presets
            self.session.commit()

    # ── Importação em lote via CSV ───────────────────────────────────────

    def importar_csv(self, texto: str) -> tuple[list[str], list[str], list[str]]:
        """
        Lê CSV (separador ; ou ,) e cria os NVRs válidos que ainda não existem.
        Colunas esperadas:
          nvr_id | nome | site | ip | porta | usuario | senha | use_https | ativo
        Retorna (criados, ignorados, erros).
        """
        texto = texto.lstrip("\ufeff")  # remove BOM do Excel
        try:
            dialect = csv.Sniffer().sniff(texto[:512], delimiters=";,")
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(io.StringIO(texto), dialect=dialect)
        if reader.fieldnames:
            reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]

        criados, ignorados, erros = [], [], []

        for i, row in enumerate(reader, start=2):  # linha 1 = cabeçalho
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items()}

            nvr_id = row.get("nvr_id", "").replace(" ", "_")
            if not nvr_id:
                erros.append(f"Linha {i}: nvr_id vazio — ignorada.")
                continue

            ip = row.get("ip", "")
            if not ip:
                erros.append(f"Linha {i} ({nvr_id}): ip vazio — ignorada.")
                continue

            if self.buscar_por_nvr_id(nvr_id):
                ignorados.append(nvr_id)
                continue

            try:
                porta = int(row.get("porta") or 80)
            except ValueError:
                erros.append(f"Linha {i} ({nvr_id}): porta inválida — usando 80.")
                porta = 80

            self.criar(
                nvr_id=nvr_id,
                nome=row.get("nome") or nvr_id,
                site=row.get("site", ""),
                ip=ip,
                porta=porta,
                usuario=row.get("usuario") or "admin",
                senha=row.get("senha", ""),
                use_https=_parse_bool_csv(row.get("use_https", "0")),
                ativo=_parse_bool_csv(row.get("ativo", "1")),
            )
            criados.append(nvr_id)

        return criados, ignorados, erros

    # ── Helpers internos ───────────────────────────────────────────────────

    def _sincronizar_presets(self, nvr: Nvr, presets: dict[int, str]) -> None:
        """Substitui todos os presets do NVR pelos fornecidos."""
        for p in list(nvr.presets):
            self.session.delete(p)
        self.session.flush()

        for numero, nome in presets.items():
            self.session.add(NvrPreset(nvr_id=nvr.nvr_id, numero=numero, nome=nome))
