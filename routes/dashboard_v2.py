"""routes/dashboard_v2.py — Dashboard com KPIs reais (schema novo, corte final)."""
from __future__ import annotations

from flask import Blueprint, render_template, session

from core.auth import login_required
from repositories_v2.ronda_repository import RondaRepository
from repositories_v2.ocorrencia_repository import OcorrenciaRepository
from repositories_v2.monitoramento_repository import MonitoramentoRepository

dashboard_bp = Blueprint("dashboard", __name__)


def _unidade_padrao_id():
    from models_v2.unidade import Unidade
    from extensions import db
    primeira = db.session.query(Unidade).order_by(Unidade.id).first()
    return primeira.id if primeira else None


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    unidade_id = _unidade_padrao_id()
    empresa_id = session.get("empresa_id")

    rondas_hoje = 0
    cameras_online, cameras_total = 0, 0
    resumo_ocorrencias = {}

    if unidade_id:
        rondas_hoje = RondaRepository().contar_por_status(unidade_id, "finalizada") \
            + RondaRepository().contar_por_status(unidade_id, "com_alertas")
        cameras_online, cameras_total = MonitoramentoRepository().contar_cameras_online(unidade_id)
    if empresa_id:
        resumo_ocorrencias = OcorrenciaRepository().resumo_por_status(empresa_id)

    return render_template(
        "dashboard_v2.html",
        rondas_hoje=rondas_hoje,
        cameras_online=cameras_online,
        cameras_total=cameras_total,
        resumo_ocorrencias=resumo_ocorrencias,
    )
