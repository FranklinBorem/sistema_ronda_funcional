"""
repositories_v2/ocorrencia_repository.py — Gestão de Ocorrência
(listagem, tratativa) e Integracao (configuração de notificação por
empresa) — schema novo, Fase E da religação.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from models_v2.ocorrencia import Ocorrencia
from models_v2.notificacao import Integracao, Notificacao
from .base import BaseRepositoryV2


class OcorrenciaRepository(BaseRepositoryV2):

    def listar_por_empresa(
        self, empresa_id: int, status: str | None = None, limite: int = 100
    ) -> list[Ocorrencia]:
        q = self.session.query(Ocorrencia).filter_by(empresa_id=empresa_id)
        if status:
            q = q.filter_by(status=status)
        return q.order_by(Ocorrencia.aberto_em.desc()).limit(limite).all()

    def buscar_por_id(self, ocorrencia_id: int) -> Optional[Ocorrencia]:
        return self.session.get(Ocorrencia, ocorrencia_id)

    def tratar(
        self, ocorrencia_id: int, responsavel_id: int, status: str = "em_tratamento"
    ) -> Ocorrencia | None:
        ocorrencia = self.session.get(Ocorrencia, ocorrencia_id)
        if ocorrencia is None:
            return None
        ocorrencia.responsavel_id = responsavel_id
        ocorrencia.status = status
        self.session.flush()
        return ocorrencia

    def encerrar(self, ocorrencia_id: int) -> Ocorrencia | None:
        ocorrencia = self.session.get(Ocorrencia, ocorrencia_id)
        if ocorrencia is None:
            return None
        ocorrencia.status = "resolvida"
        ocorrencia.tratado_em = datetime.now(timezone.utc)
        self.session.flush()
        return ocorrencia

    def resumo_por_status(self, empresa_id: int) -> dict[str, int]:
        from sqlalchemy import func
        linhas = (
            self.session.query(Ocorrencia.status, func.count(Ocorrencia.id))
            .filter_by(empresa_id=empresa_id)
            .group_by(Ocorrencia.status)
            .all()
        )
        return {status: total for status, total in linhas}


class IntegracaoRepository(BaseRepositoryV2):

    def buscar_ativa(self, empresa_id: int, tipo: str) -> Optional[Integracao]:
        return (
            self.session.query(Integracao)
            .filter_by(empresa_id=empresa_id, tipo=tipo, ativo=True)
            .first()
        )

    def configurar(self, empresa_id: int, tipo: str, configuracao: dict) -> Integracao:
        """Cria ou atualiza a configuração de um tipo de integração para a empresa."""
        existente = (
            self.session.query(Integracao)
            .filter_by(empresa_id=empresa_id, tipo=tipo)
            .first()
        )
        if existente:
            existente.configuracao = configuracao
            existente.ativo = True
            self.session.flush()
            return existente

        integracao = Integracao(
            empresa_id=empresa_id, tipo=tipo, configuracao=configuracao, ativo=True,
        )
        self.session.add(integracao)
        self.session.flush()
        return integracao

    def registrar_notificacao(
        self, ocorrencia_id: int, integracao_id: int, status_envio: str
    ) -> Notificacao:
        notificacao = Notificacao(
            ocorrencia_id=ocorrencia_id, integracao_id=integracao_id,
            status_envio=status_envio,
        )
        self.session.add(notificacao)
        self.session.flush()
        return notificacao
