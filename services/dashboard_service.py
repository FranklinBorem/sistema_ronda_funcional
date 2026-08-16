"""
services/dashboard_service.py — Dados do dashboard principal.

Responsabilidade única: montar o dicionário de contexto que a rota
/dashboard entrega ao template. Toda persistência é delegada a
AlertaRepository, RondaRepository e NvrRepository.

Não importa sqlite3, get_db, nvr_config nem queries SQL — apenas repositórios.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from repositories.alerta_repository import AlertaRepository
from repositories.nvr_repository import NvrRepository
from repositories.ronda_repository import RondaRepository


class DashboardService:
    """Monta os dados do dashboard sem acoplar regra de negócio ao Flask."""

    def __init__(
        self,
        dias: int = 30,
        alerta_repo: AlertaRepository | None = None,
        ronda_repo: RondaRepository | None = None,
        nvr_repo: NvrRepository | None = None,
    ) -> None:
        self.dias = dias
        self._alerta_repo = alerta_repo or AlertaRepository()
        self._ronda_repo  = ronda_repo  or RondaRepository()
        self._nvr_repo    = nvr_repo    or NvrRepository()

    # ── API pública ────────────────────────────────────────────────────────

    def build_context(self) -> dict:
        rondas = self._ronda_repo.listar_historico(limite=20)
        return {
            "rondas": rondas,
            "kpi":    self._build_kpis(),
            "dias":   self.dias,
        }

    # ── KPIs ───────────────────────────────────────────────────────────────

    def _build_kpis(self) -> dict:
        return {
            **self._build_ronda_kpis(),
            **self._build_alerta_kpis(),
            "nvrs_ativos": self._nvr_repo.listar(apenas_ativos=True).__len__(),
        }

    def _build_ronda_kpis(self) -> dict:
        por_status  = self._ronda_repo.contar_por_status()
        total       = sum(por_status.values())
        ok          = por_status.get("finalizada", 0)
        alerta      = por_status.get("com_alertas", 0)
        hoje        = datetime.utcnow().strftime("%Y-%m-%d")
        rondas_hoje = len(self._ronda_repo.listar_filtrado(data_ini=hoje, limite=9999))

        return {
            "rondas_total":    total,
            "rondas_ok":       ok,
            "rondas_alerta":   alerta,
            "rondas_hoje":     rondas_hoje,
            "tempo_medio_min": self._tempo_medio_ronda(),
        }

    def _build_alerta_kpis(self) -> dict:
        # NOTA: desde a unificação de status (StatusAlerta agora só tem
        # pendente/tratado), AlertaRepository.resumo() retorna:
        #   total, pendentes, tratados (confirmados + falso_positivo juntos),
        #   falso_positivos (subconjunto de tratados)
        # "Confirmados" (só o que foi tratado sem ser falso positivo) é
        # derivado aqui: tratados - falso_positivos.
        try:
            resumo   = self._alerta_repo.resumo()
            top_nvrs = self._top_nvrs_formatado()
            labels, valores = self._grafico_ultimos_dias()
        except Exception:
            resumo   = {"total": 0, "pendentes": 0, "tratados": 0, "falso_positivos": 0}
            top_nvrs = []
            labels, valores = [], []

        total       = resumo["total"]
        falsas      = resumo.get("falso_positivos", 0)
        confirmados = resumo["tratados"] - falsas
        precisao    = round(confirmados / total * 100) if total else 0

        return {
            "det_total":       total,
            "det_pendente":    resumo["pendentes"],
            "det_tratando":    falsas,
            "det_tratado":     confirmados,
            "confirmados":     confirmados,
            "falsos_positivos": falsas,
            "precisao":        precisao,
            "top_nvrs":        top_nvrs,
            "grafico_labels":  labels,
            "grafico_valores": valores,
        }

    # ── Helpers ────────────────────────────────────────────────────────────

    def _tempo_medio_ronda(self) -> float:
        corte  = (datetime.utcnow() - timedelta(days=self.dias)).strftime("%Y-%m-%d")
        rondas = self._ronda_repo.listar_filtrado(data_ini=corte, status="finalizada", limite=9999)
        diffs  = [
            (r.finalizada_em - r.iniciada_em).total_seconds() / 60
            for r in rondas
            if r.iniciada_em and r.finalizada_em
        ]
        return round(sum(diffs) / len(diffs), 1) if diffs else 0.0

    def _top_nvrs_formatado(self) -> list[dict]:
        rows = self._alerta_repo.top_nvrs_alertas(dias=self.dias, limite=5)
        if not rows:
            return []
        max_total = rows[0]["total"] or 1
        return [
            {"nome": r["nvr"], "total": r["total"], "pct": round(r["total"] / max_total * 100)}
            for r in rows
        ]

    def _grafico_ultimos_dias(self) -> tuple[list[str], list[int]]:
        rows   = self._alerta_repo.alertas_por_dia(dias=14)
        por_dia: dict[str, int] = {r["dia"]: r["total"] for r in rows}
        labels, valores = [], []
        for i in range(13, -1, -1):
            data = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            labels.append(data[5:])
            valores.append(por_dia.get(data, 0))
        return labels, valores
