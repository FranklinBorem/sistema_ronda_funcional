"""
routes/alarmes.py — Central de Alarmes.

Substitui alarmes_routes.py.
Sem sqlite3, sem _build_filtros() inline, sem get_db() —
toda persistência delegada ao AlertaRepository via AlarmeService
(ou diretamente ao repository, pois não há lógica de negócio adicional aqui).
"""

from __future__ import annotations

from flask import (
    Blueprint, jsonify, render_template,
    request, session,
)

from core.auth import login_required
from models.alerta import StatusAlerta, MotivoTratamento
from repositories import AlertaRepository

alarmes_bp = Blueprint("alarmes", __name__)


def _repo() -> AlertaRepository:
    """Instância por request — seguro pois db.session é thread-local."""
    return AlertaRepository()


# ── Página principal ──────────────────────────────────────────────────────

@alarmes_bp.route("/alarmes")
@login_required
def central_alarmes():
    repo   = _repo()
    resumo = repo.resumo()
    return render_template(
        "alarmes.html",
        ufvs=repo.listar_ufvs(),
        nvrs=repo.listar_nvrs(),
        total=resumo["total"],
        pendentes=resumo["pendentes"],
        tratados=resumo["tratados"],
        falso_positivos=resumo["falso_positivos"],
    )


# ── API — listagem paginada ────────────────────────────────────────────────

@alarmes_bp.route("/api/alarmes")
@login_required
def api_listar_alertas():
    args = request.args
    alertas, total = _repo().listar(
        status=args.get("status"),
        motivo=args.get("motivo"),
        ufv=args.get("ufv"),
        nvr_id=args.get("nvr"),
        data_inicio=args.get("data_inicio"),
        data_fim=args.get("data_fim"),
        page=int(args.get("page", 1)),
        per_page=int(args.get("per_page", 20)),
    )
    per_page = int(args.get("per_page", 20))
    return jsonify({
        "total":    total,
        "page":     int(args.get("page", 1)),
        "per_page": per_page,
        "pages":    (total + per_page - 1) // per_page,
        "alertas":  [a.to_dict() for a in alertas],
    })


# ── API — detalhe ─────────────────────────────────────────────────────────

@alarmes_bp.route("/api/alarmes/<int:alerta_id>")
@login_required
def api_detalhe_alerta(alerta_id: int):
    alerta = _repo().buscar_por_id(alerta_id)
    if not alerta:
        return jsonify({"erro": "Alerta não encontrado"}), 404
    return jsonify(alerta.to_dict())


# ── API — tratar ──────────────────────────────────────────────────────────

@alarmes_bp.route("/api/alarmes/<int:alerta_id>/tratar", methods=["POST"])
@login_required
def api_tratar_alerta(alerta_id: int):
    data       = request.get_json(force=True) or {}
    tratativa  = (data.get("tratativa") or "").strip()
    status_raw = (data.get("status") or "pendente").strip().lower()
    motivo_raw = (data.get("motivo") or "").strip().lower()

    if "tratado" in status_raw or "falsa" in status_raw:
        novo_status = StatusAlerta.TRATADO
    elif "pendente" in status_raw:
        novo_status = StatusAlerta.PENDENTE
    else:
        return jsonify({"erro": "Status inválido"}), 400

    motivo = None
    if novo_status == StatusAlerta.TRATADO:
        # "falsa"/"falso" cobre tanto o front novo (campo motivo) quanto
        # uma eventual chamada antiga que ainda mande status="deteccao_falsa"
        if "falsa" in status_raw or "falso" in motivo_raw:
            motivo = MotivoTratamento.FALSO_POSITIVO
        else:
            motivo = MotivoTratamento.CONFIRMADO

    responsavel = session.get("monitor_nome", "Desconhecido")
    repo        = _repo()
    alerta      = repo.tratar(alerta_id, novo_status, tratativa, responsavel, motivo)

    if not alerta:
        return jsonify({"erro": "Alerta não encontrado"}), 404

    from extensions import db
    db.session.commit()

    return jsonify({
        "ok": True,
        "status": alerta.status,
        "motivo_tratamento": alerta.motivo_tratamento,
    })


# ── API — reabrir ─────────────────────────────────────────────────────────

@alarmes_bp.route("/api/alarmes/<int:alerta_id>/reabrir", methods=["POST"])
@login_required
def api_reabrir_alerta(alerta_id: int):
    alerta = _repo().reabrir(alerta_id)
    if not alerta:
        return jsonify({"erro": "Alerta não encontrado"}), 404

    from extensions import db
    db.session.commit()

    return jsonify({"ok": True})


# ── API — resumo (polling dos cards) ─────────────────────────────────────

@alarmes_bp.route("/api/alarmes/resumo")
@login_required
def api_resumo():
    return jsonify(_repo().resumo())
