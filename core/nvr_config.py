"""
Configuracao centralizada das speed domes.

As cameras sao cadastradas na tabela `nvrs` (PostgreSQL) e seus presets na
tabela `nvr_presets`. Este modulo expoe a mesma interface publica de antes
(NVRConfig, NVRS, buscar_nvr) para nao exigir mudancas em quem ja importa
daqui (routes/ronda_loop.py, core/ronda_multi_nvr.py, etc.), trocando apenas
a origem dos dados: do CSV/XLSX para o banco.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class NVRConfig:
    id: str
    nome: str
    ip: str
    usuario: str
    senha: str
    ptz_channel: int = 1
    snapshot_channel: str = "501"
    presets: Dict[int, str] = field(default_factory=dict)
    tempo_espera: int = 5
    timeout: int = 10
    site: str = ""
    ativo: bool = True
    observacoes: str = ""


def _resolver_segredo(valor: str) -> str:
    """
    Permite usar env:NOME_DA_VARIAVEL no banco para nao deixar senha exposta
    em texto plano na tabela. Se a variavel nao existir, retorna string vazia.
    """
    if valor and valor.startswith("env:"):
        return os.getenv(valor[4:], "")
    return valor


def _nvr_para_config(nvr) -> NVRConfig:
    """Converte uma instancia do model Nvr (SQLAlchemy) em NVRConfig."""
    presets = {preset.numero: preset.nome for preset in nvr.presets}

    return NVRConfig(
        id=nvr.nvr_id,
        site=nvr.site or "",
        nome=nvr.nome,
        ip=nvr.ip,
        usuario=nvr.usuario,
        senha=_resolver_segredo(nvr.senha),
        presets=presets,
        tempo_espera=nvr.tempo_espera,
        timeout=nvr.timeout,
        ativo=nvr.ativo,
    )


def carregar_nvrs(incluir_inativos: bool = False) -> list[NVRConfig]:
    """
    Carrega os NVRs cadastrados no banco PostgreSQL.

    Precisa ser chamada dentro do contexto da aplicacao Flask
    (app.app_context()), pois depende da sessao do SQLAlchemy.
    """
    from models.nvr import Nvr  # import local para evitar import circular

    query = Nvr.query
    if not incluir_inativos:
        query = query.filter_by(ativo=True)

    nvrs_db = query.order_by(Nvr.site, Nvr.nome).all()
    return [_nvr_para_config(nvr) for nvr in nvrs_db]


def buscar_nvr(nvr_id: str) -> NVRConfig | None:
    from models.nvr import Nvr  # import local para evitar import circular

    nvr = Nvr.query.filter_by(nvr_id=nvr_id).first()
    return _nvr_para_config(nvr) if nvr else None


def listar_nvrs(incluir_inativos: bool = False) -> list[NVRConfig]:
    """Alias explicito de carregar_nvrs, para compatibilidade com chamadas
    no estilo nvr_db.listar_nvrs() usadas em outras partes do projeto."""
    return carregar_nvrs(incluir_inativos=incluir_inativos)


# NOTA IMPORTANTE:
# Diferente da versao antiga (CSV/XLSX), NVRS deixou de ser uma lista
# carregada automaticamente na importacao do modulo, pois isso exigiria
# contexto de aplicacao Flask/SQLAlchemy disponivel no momento do import
# (o que falha se este modulo for importado antes do app estar criado).
#
# Em vez de "from core.nvr_config import NVRS", use:
#     from core.nvr_config import carregar_nvrs
#     nvrs = carregar_nvrs()
#
# Se algum arquivo do projeto ainda importar NVRS diretamente, ajuste essa
# importacao para chamar carregar_nvrs() dentro de uma rota ou funcao que
# já esteja rodando dentro do contexto da aplicacao.
