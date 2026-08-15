"""
repositories_v2/ronda_repository.py — Acesso a dados de Ronda/
ResultadoRonda + registro de ocorrência gerada por detecção de IA
(schema novo).

Substitui repositories/ronda_repository.py + parte de
repositories/alerta_repository.py no schema reconstruído.

DECISÃO DE MAPEAMENTO (Alerta antigo -> Ocorrencia):
O `Alerta` antigo guardava uma contagem agregada de pessoas por
preset/ronda (não uma detecção individual com confiança), então o
mapeamento natural é para uma linha em `Ocorrencia`
(origem='deteccao_ia'), não para `EventoIA` (que é por detecção
individual, com classe+confiança — ver docs/architecture/ia.md).
Esta função não usa EventoIA/RegraDeteccao ainda porque essa
granularidade (regra por câmera) é trabalho da Fase 5 (IA avançada),
fora do escopo desta religação.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from models_v2.ronda import Ronda, ResultadoRonda, STATUS_RONDA_VALIDOS
from models_v2.ocorrencia import Ocorrencia
from models_v2.nvr import Nvr
from .base import BaseRepositoryV2


class RondaRepository(BaseRepositoryV2):

    # ── Ronda ────────────────────────────────────────────────────────────

    def criar(self, unidade_id: int, usuario_id: int | None = None) -> Ronda:
        ronda = Ronda(unidade_id=unidade_id, usuario_id=usuario_id, status="em_andamento")
        self.session.add(ronda)
        self.session.flush()
        return ronda

    def buscar_por_id(self, ronda_id: int) -> Optional[Ronda]:
        return self.session.get(Ronda, ronda_id)

    def finalizar(self, ronda_id: int, status: str) -> None:
        if status not in STATUS_RONDA_VALIDOS:
            raise ValueError(f"status inválido: {status!r} (válidos: {STATUS_RONDA_VALIDOS})")
        ronda = self.session.get(Ronda, ronda_id)
        if ronda is None:
            return
        ronda.status = status
        ronda.finalizado_em = datetime.utcnow()
        self.session.flush()

    def listar_por_unidade(self, unidade_id: int, limite: int = 50) -> list[Ronda]:
        return (
            self.session.query(Ronda)
            .filter_by(unidade_id=unidade_id)
            .order_by(Ronda.iniciado_em.desc())
            .limit(limite)
            .all()
        )

    def contar_por_status(self, unidade_id: int, status: str) -> int:
        return (
            self.session.query(Ronda)
            .filter_by(unidade_id=unidade_id, status=status)
            .count()
        )

    # ── ResultadoRonda (por NVR) ─────────────────────────────────────────

    def registrar_resultado_nvr(
        self,
        ronda_id: int | None,
        nvr_id: int,
        status: str,
        imagens_ref: dict | None = None,
    ) -> ResultadoRonda | None:
        if not ronda_id:
            return None
        resultado = ResultadoRonda(
            ronda_id=ronda_id, nvr_id=nvr_id, status=status, imagens_ref=imagens_ref,
        )
        self.session.add(resultado)
        self.session.flush()
        return resultado

    # ── Ocorrência gerada por detecção de IA (substitui Alerta) ──────────

    def registrar_ocorrencia_deteccao(
        self,
        nvr_id: int,
        pessoas: int,
        local_preset: str,
        imagem_path: str | None,
        detectado_em: datetime,
        ronda_id: int | None = None,
    ) -> Ocorrencia | None:
        """
        Cria uma Ocorrencia (origem='deteccao_ia') a partir de uma
        detecção durante a ronda. Resolve empresa_id/unidade_id a
        partir do nvr_id (via Nvr -> Unidade -> Empresa).
        """
        nvr = self.session.get(Nvr, nvr_id)
        if nvr is None:
            return None
        unidade = nvr.unidade
        ocorrencia = Ocorrencia(
            empresa_id=unidade.empresa_id,
            unidade_id=unidade.id,
            origem="deteccao_ia",
            tipo="pessoa",
            prioridade="alta" if pessoas > 0 else "media",
            status="aberta",
            aberto_em=detectado_em,
        )
        self.session.add(ocorrencia)
        self.session.flush()
        return ocorrencia
