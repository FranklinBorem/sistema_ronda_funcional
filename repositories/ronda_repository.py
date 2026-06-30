"""
repositories/ronda_repository.py — Acesso a dados de rondas.

Substitui as queries espalhadas em:
  - core.py (init_db / schema)
  - ronda_multi_nvr.py (salvar_ronda_nvr, atualizar_ronda_pai)
  - ronda_loop.py (_criar_ronda_pai)
  - services/ronda_service.py (queries inline)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import desc

from models.ronda import Ronda, RondaNvr, StatusRonda, StatusRondaNvr
from .base import BaseRepository


class RondaRepository(BaseRepository):

    # ── Ronda pai ──────────────────────────────────────────────────────────

    def criar(
        self,
        monitor_id: int,
        monitor_nome: str,
        turno: str,
        pasta: str,
    ) -> Ronda:
        """
        Cria uma ronda pai com status em_andamento.
        Usado pelo ronda_loop.py e pelo RondaService.
        """
        ronda = Ronda(
            monitor_id=monitor_id,
            monitor_nome=monitor_nome,
            turno=turno,
            pasta=pasta,
            iniciada_em=datetime.utcnow(),
            status=StatusRonda.EM_ANDAMENTO.value,
        )
        self.session.add(ronda)
        self.session.flush()   # gera o ID imediatamente
        return ronda

    def buscar_por_id(self, ronda_id: int) -> Optional[Ronda]:
        return self.session.get(Ronda, ronda_id)

    def listar_historico(self, limite: int = 200) -> list[Ronda]:
        """Retorna as N rondas mais recentes para a tela de histórico."""
        return (
            self.session
            .query(Ronda)
            .order_by(desc(Ronda.iniciada_em))
            .limit(limite)
            .all()
        )

    def listar_filtrado(
        self,
        data_ini: str | None = None,
        data_fim: str | None = None,
        turno: str | None = None,
        monitor_nome: str | None = None,
        status: str | None = None,
        limite: int = 200,
    ) -> list[Ronda]:
        """
        Listagem com filtros opcionais — usada pela rota de e-mail
        e por relatórios customizados.
        """
        q = self.session.query(Ronda)

        if data_ini:
            q = q.filter(Ronda.iniciada_em >= data_ini)
        if data_fim:
            q = q.filter(Ronda.iniciada_em <= f"{data_fim} 23:59:59")
        if turno:
            q = q.filter(Ronda.turno == turno)
        if monitor_nome:
            q = q.filter(Ronda.monitor_nome == monitor_nome)
        if status:
            q = q.filter(Ronda.status == status)

        return (
            q.order_by(desc(Ronda.iniciada_em))
            .limit(limite)
            .all()
        )

    def finalizar(
        self,
        ronda_id: int,
        status: StatusRonda = StatusRonda.FINALIZADA,
    ) -> None:
        """
        Atualiza status e finalizada_em da ronda pai.
        Substitui atualizar_ronda_pai() de ronda_multi_nvr.py.
        """
        ronda = self.session.get(Ronda, ronda_id)
        if ronda:
            ronda.finalizar(status)

    # ── Ronda NVR ─────────────────────────────────────────────────────────

    def registrar_nvr(
        self,
        ronda_id: int | None,
        nvr_id: str,
        nvr_nome: str,
        status: str,
        invasoes: int,
        pasta: str,
    ) -> RondaNvr:
        """
        Salva o resultado de um NVR ao final da sua thread.
        Substitui salvar_ronda_nvr() de ronda_multi_nvr.py.
        """
        nvr = RondaNvr(
            ronda_id=ronda_id,
            nvr_id=nvr_id,
            nvr_nome=nvr_nome,
            status=status,
            invasoes=invasoes,
            pasta=pasta,
            finalizada_em=datetime.utcnow(),
        )
        self.session.add(nvr)
        self.session.flush()
        return nvr

    def listar_nvrs_por_ronda(self, ronda_id: int) -> list[RondaNvr]:
        return (
            self.session
            .query(RondaNvr)
            .filter_by(ronda_id=ronda_id)
            .all()
        )

    # ── Métricas para dashboard ────────────────────────────────────────────

    def contar_por_status(self) -> dict[str, int]:
        """Retorna {status: contagem} para todos os status existentes."""
        from sqlalchemy import func
        rows = (
            self.session
            .query(Ronda.status, func.count(Ronda.id))
            .group_by(Ronda.status)
            .all()
        )
        return {status: count for status, count in rows}

    def total_por_monitor(self, dias: int = 30) -> list[dict]:
        """Rondas agrupadas por monitor nos últimos N dias."""
        from sqlalchemy import func
        from datetime import timedelta
        limite = datetime.utcnow() - timedelta(days=dias)
        rows = (
            self.session
            .query(Ronda.monitor_nome, func.count(Ronda.id).label("total"))
            .filter(Ronda.iniciada_em >= limite)
            .group_by(Ronda.monitor_nome)
            .order_by(desc("total"))
            .all()
        )
        return [{"monitor": r.monitor_nome, "total": r.total} for r in rows]

    def rondas_por_dia(self, dias: int = 30) -> list[dict]:
        """Contagem diária de rondas para o gráfico do dashboard."""
        from sqlalchemy import func, cast, Date
        from datetime import timedelta
        limite = datetime.utcnow() - timedelta(days=dias)
        rows = (
            self.session
            .query(
                cast(Ronda.iniciada_em, Date).label("dia"),
                func.count(Ronda.id).label("total"),
            )
            .filter(Ronda.iniciada_em >= limite)
            .group_by("dia")
            .order_by("dia")
            .all()
        )
        return [{"dia": str(r.dia), "total": r.total} for r in rows]
