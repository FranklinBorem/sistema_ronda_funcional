"""
routes/ronda_loop.py — Controle do loop de ronda contínua.

Substitui ronda_loop_routes.py.

As funções do motor (iniciar_loop, parar_loop, status_loop) continuam
sendo importadas diretamente de core.ronda_loop — o loop é estado
global de processo e não precisa de um service intermediário.
"""
from __future__ import annotations

from flask import (
    Blueprint, jsonify, render_template,
    request, session,
)

from core.auth import login_required
from core.nvr_config import carregar_nvrs
from core.ronda_loop import iniciar_loop, parar_loop, status_loop

ronda_loop_bp = Blueprint("ronda_loop", __name__)


# ── Página de controle ──────────────────────────────────────────────────

@ronda_loop_bp.route("/ronda-loop")
@login_required
def pagina_loop():
    nvrs_disponiveis = [
        {"id": n.id, "nome": n.nome, "site": n.site, "ip": n.ip}
        for n in carregar_nvrs()
    ]
    return render_template(
        "ronda_loop.html",
        nvrs=nvrs_disponiveis,
        monitor_nome=session.get("monitor_nome", ""),
        turno=session.get("monitor_turno", ""),
    )


# ── API — iniciar ───────────────────────────────────────────────────────

@ronda_loop_bp.route("/api/ronda-loop/iniciar", methods=["POST"])
@login_required
def api_iniciar():
    data = request.get_json(force=True) or {}
    resultado = iniciar_loop(
        monitor_id=session.get("monitor_id"),
        monitor_nome=data.get("monitor_nome") or session.get("monitor_nome", "Não informado"),
        turno=data.get("turno") or session.get("monitor_turno", "Não informado"),
        nvr_ids=data.get("nvr_ids") or None,
    )
    return jsonify(resultado)


# ── API — parar ──────────────────────────────────────────────────────────

@ronda_loop_bp.route("/api/ronda-loop/parar", methods=["POST"])
@login_required
def api_parar():
    return jsonify(parar_loop())


# ── API — status ─────────────────────────────────────────────────────────

@ronda_loop_bp.route("/api/ronda-loop/status")
@login_required
def api_status():
    return jsonify(status_loop())
