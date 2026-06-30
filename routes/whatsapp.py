"""
routes/whatsapp.py — Conector WhatsApp e monitor de grupos.

Substitui whatsapp_routes.py.
Sem sqlite3, sem get_db() — delegado ao WhatsAppMonitorService.
O commit da sessão é feito aqui, após cada operação de escrita,
mantendo a rota responsável pelo ciclo de transação.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from core.auth import login_required
from extensions import db
from services import WhatsAppMonitorService

whatsapp_bp = Blueprint("whatsapp", __name__)


@whatsapp_bp.route("/mensagens", methods=["POST"])
def receber_mensagem():
    payload, status_code = WhatsAppMonitorService().registrar_mensagem(
        request.json or {}
    )
    if status_code == 200 and payload.get("status") == "ok":
        db.session.commit()
    return jsonify(payload), status_code


@whatsapp_bp.route("/heartbeat", methods=["POST"])
def heartbeat():
    timestamp = (request.json or {}).get("timestamp")
    payload = WhatsAppMonitorService().registrar_heartbeat(timestamp)
    db.session.commit()
    return jsonify(payload), 200


@whatsapp_bp.route("/monitor-whatsapp")
@login_required
def monitor_whatsapp():
    context = WhatsAppMonitorService().montar_contexto_monitor()
    return render_template("monitor_whatsapp.html", **context)
