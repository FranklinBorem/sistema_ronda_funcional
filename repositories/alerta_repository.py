"""
repositories/alerta_repository.py — Acesso a dados de alertas.

Substitui:
  - alarmes_schema.py (registrar_alerta, queries diretas sqlite3)
  - alarmes_routes.py (queries inline _build_filtros)

Este repository é o único chamado diretamente pelo motor de ronda
(ronda_multi_nvr.py) fora do Flask context — a injeção de sessão
da BaseRepository resolve isso de forma transparente.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import desc, func

from models.alerta import Alerta, StatusAlerta
from .base import BaseRepository


class AlertaRepository(BaseRepository):

    # ── Escrita ────────────────────────────────────────────────────────────

    def registrar(
        self,
        nvr_id: str,
        nvr_nome: str,
        local_preset: str,
        pessoas: int,
        detectado_em: datetime,
        ronda_id: int | None = None,
        ufv: str | None = None,
        imagem_path: str | None = None,
    ) -> Alerta:
        """
        Persiste um alerta gerado pelo YOLO.
        Substitui registrar_alerta() de alarmes_schema.py.
        Seguro para uso em threads (injetar Session explícita).
        """
        alerta = Alerta(
            ronda_id=ronda_id,
            nvr_id=nvr_id,
            nvr_nome=nvr_nome,
            ufv=ufv,
            local_preset=local_preset,
            pessoas=pessoas,
            imagem_path=imagem_path,
            detectado_em=detectado_em,
            status=StatusAlerta.PENDENTE.value,
        )
        self.session.add(alerta)
        self.session.flush()
        return alerta

    def tratar(
        self,
        alerta_id: int,
        novo_status: StatusAlerta,
        tratativa: str,
        responsavel: str,
    ) -> Optional[Alerta]:
        """Registra tratativa. Retorna None se o alerta não existir."""
        alerta = self.session.get(Alerta, alerta_id)
        if not alerta:
            return None
        alerta.tratar(novo_status, tratativa, responsavel)
        return alerta

    def reabrir(self, alerta_id: int) -> Optional[Alerta]:
        alerta = self.session.get(Alerta, alerta_id)
        if not alerta:
            return None
        alerta.reabrir()
        return alerta

    # ── Leitura — item único ───────────────────────────────────────────────

    def buscar_por_id(self, alerta_id: int) -> Optional[Alerta]:
        return self.session.get(Alerta, alerta_id)

    # ── Leitura — listagem paginada com filtros ────────────────────────────

    def listar(
        self,
        status: str | None = None,
        ufv: str | None = None,
        nvr_id: str | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Alerta], int]:
        """
        Retorna (alertas_da_página, total).
        Substitui _build_filtros() + queries de alarmes_routes.py.
        Só inclui detecções reais de pessoas (pessoas > 0).
        """
        q = (
            self.session
            .query(Alerta)
            .filter(Alerta.pessoas > 0)
        )

        if status and status != "todos":
            q = q.filter(Alerta.status == status)
        if ufv:
            q = q.filter(Alerta.ufv == ufv)
        if nvr_id:
            q = q.filter(Alerta.nvr_id == nvr_id)
        if data_inicio:
            q = q.filter(Alerta.detectado_em >= data_inicio)
        if data_fim:
            q = q.filter(Alerta.detectado_em <= f"{data_fim} 23:59:59")

        total = q.count()
        alertas = (
            q.order_by(desc(Alerta.detectado_em))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return alertas, total

    # ── Leitura — filtros disponíveis ─────────────────────────────────────

    def listar_ufvs(self) -> list[str]:
        """Valores distintos de UFV para preencher o filtro da tela."""
        rows = (
            self.session
            .query(Alerta.ufv)
            .filter(Alerta.ufv.isnot(None), Alerta.pessoas > 0)
            .distinct()
            .order_by(Alerta.ufv)
            .all()
        )
        return [r.ufv for r in rows]

    def listar_nvrs(self) -> list[dict]:
        """Pares (nvr_id, nvr_nome) distintos para o filtro da tela."""
        rows = (
            self.session
            .query(Alerta.nvr_id, Alerta.nvr_nome)
            .filter(Alerta.pessoas > 0)
            .distinct()
            .order_by(Alerta.nvr_nome)
            .all()
        )
        return [{"nvr_id": r.nvr_id, "nvr_nome": r.nvr_nome} for r in rows]

    # ── Contadores para os cards do topo ──────────────────────────────────

    def resumo(self) -> dict[str, int]:
        """
        Retorna contadores por status para atualização em tempo real.
        Substitui as 4 queries separadas de api_resumo() e central_alarmes().
        """
        rows = (
            self.session
            .query(Alerta.status, func.count(Alerta.id))
            .filter(Alerta.pessoas > 0)
            .group_by(Alerta.status)
            .all()
        )
        base = {
            StatusAlerta.PENDENTE.value:       0,
            StatusAlerta.TRATADO.value:        0,
            StatusAlerta.DETECCAO_FALSA.value: 0,
        }
        for status, count in rows:
            base[status] = count

        total = sum(base.values())
        return {
            "total":            total,
            "pendentes":        base[StatusAlerta.PENDENTE.value],
            "tratados":         base[StatusAlerta.TRATADO.value],
            "deteccoes_falsas": base[StatusAlerta.DETECCAO_FALSA.value],
        }

    # ── Métricas para dashboard ────────────────────────────────────────────

    def alertas_por_dia(self, dias: int = 30) -> list[dict]:
        """Contagem diária de alertas para o gráfico do dashboard."""
        from sqlalchemy import cast, Date
        from datetime import timedelta
        limite = datetime.utcnow() - timedelta(days=dias)
        rows = (
            self.session
            .query(
                cast(Alerta.detectado_em, Date).label("dia"),
                func.count(Alerta.id).label("total"),
            )
            .filter(Alerta.detectado_em >= limite, Alerta.pessoas > 0)
            .group_by("dia")
            .order_by("dia")
            .all()
        )
        return [{"dia": str(r.dia), "total": r.total} for r in rows]

    def top_nvrs_alertas(self, dias: int = 30, limite: int = 5) -> list[dict]:
        """NVRs com mais alertas nos últimos N dias — widget do dashboard."""
        from datetime import timedelta
        corte = datetime.utcnow() - timedelta(days=dias)
        rows = (
            self.session
            .query(Alerta.nvr_nome, func.count(Alerta.id).label("total"))
            .filter(Alerta.detectado_em >= corte, Alerta.pessoas > 0)
            .group_by(Alerta.nvr_nome)
            .order_by(desc("total"))
            .limit(limite)
            .all()
        )
        return [{"nvr": r.nvr_nome, "total": r.total} for r in rows]
