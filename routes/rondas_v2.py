"""
routes/rondas_v2.py — Disparo e consulta de rondas (schema novo).

Substitui, quando religado, /iniciar_ronda_multi e /api/ronda/<id>/status
de routes/rondas.py. Não registrado em routes/__init__.py ainda — ver
docs/decisions/decisoes-pendentes.md sobre religação atômica.
"""

from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, request, session, url_for

from core.auth import login_required
from services_v2.ronda_service import RondaService
from repositories_v2.ronda_repository import RondaRepository

rondas_v2_bp = Blueprint("rondas_v2", __name__)

_service = RondaService()
_repo = RondaRepository()


def _unidade_padrao_id() -> int | None:
    from models_v2.unidade import Unidade
    from extensions import db
    primeira = db.session.query(Unidade).order_by(Unidade.id).first()
    return primeira.id if primeira else None


@rondas_v2_bp.route("/iniciar_ronda_multi", methods=["POST"])
@login_required
def iniciar_ronda_multi():
    unidade_id = _unidade_padrao_id()
    if not unidade_id:
        flash("Cadastre uma Unidade antes de iniciar uma ronda.", "warning")
        return redirect(request.referrer or url_for("equipamentos.listar"))

    ronda_id = _service.iniciar_ronda_multi(
        unidade_id=unidade_id,
        usuario_id=session.get("monitor_id"),
        monitor_nome=session.get("monitor_nome", "Não informado"),
        turno=session.get("monitor_turno", "Não informado"),
    )
    flash(f"Ronda #{ronda_id} iniciada.", "success")
    return redirect(request.referrer or url_for("equipamentos.listar"))


@rondas_v2_bp.route("/api/ronda/<int:ronda_id>/status")
@login_required
def api_status_ronda(ronda_id: int):
    ronda = _repo.buscar_por_id(ronda_id)
    if not ronda:
        return jsonify({"erro": "ronda não encontrada"}), 404
    return jsonify(ronda.to_dict())
