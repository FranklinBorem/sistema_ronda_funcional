"""
routes/ocorrencias.py — Consulta e tratativa de Ocorrência (schema
novo, Fase E da religação). Substitui, quando religado,
routes/alarmes.py (que operava sobre o antigo Alerta). Ainda não
registrado em routes/__init__.py — religação atômica, ver
docs/decisions/decisoes-pendentes.md.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request, session

from core.auth import login_required
from repositories_v2.ocorrencia_repository import OcorrenciaRepository

ocorrencias_bp = Blueprint("ocorrencias", __name__)

_repo = OcorrenciaRepository()


@ocorrencias_bp.route("/ocorrencias")
@login_required
def listar():
    empresa_id = session.get("empresa_id")
    ocorrencias = _repo.listar_por_empresa(empresa_id) if empresa_id else []
    resumo = _repo.resumo_por_status(empresa_id) if empresa_id else {}
    return render_template("ocorrencias/listar.html", ocorrencias=ocorrencias, resumo=resumo)


@ocorrencias_bp.route("/api/ocorrencias")
@login_required
def api_listar():
    empresa_id = session.get("empresa_id")
    status = request.args.get("status")
    ocorrencias = _repo.listar_por_empresa(empresa_id, status=status) if empresa_id else []
    return jsonify({"ocorrencias": [o.to_dict() for o in ocorrencias]})


@ocorrencias_bp.route("/api/ocorrencias/<int:ocorrencia_id>/tratar", methods=["POST"])
@login_required
def api_tratar(ocorrencia_id: int):
    from extensions import db
    ocorrencia = _repo.tratar(ocorrencia_id, responsavel_id=session.get("monitor_id"))
    if not ocorrencia:
        return jsonify({"erro": "ocorrência não encontrada"}), 404
    db.session.commit()
    return jsonify(ocorrencia.to_dict())


@ocorrencias_bp.route("/api/ocorrencias/<int:ocorrencia_id>/encerrar", methods=["POST"])
@login_required
def api_encerrar(ocorrencia_id: int):
    from extensions import db
    ocorrencia = _repo.encerrar(ocorrencia_id)
    if not ocorrencia:
        return jsonify({"erro": "ocorrência não encontrada"}), 404
    db.session.commit()
    return jsonify(ocorrencia.to_dict())


@ocorrencias_bp.route("/api/ocorrencias/resumo")
@login_required
def api_resumo():
    empresa_id = session.get("empresa_id")
    return jsonify(_repo.resumo_por_status(empresa_id) if empresa_id else {})
