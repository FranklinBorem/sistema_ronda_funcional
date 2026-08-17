"""
routes/pendentes_v2.py — Blueprints ainda não religados para o schema
novo (WhatsApp) + painel de conferência (religado, dados reais).

WhatsApp depende de coordenar também o processo Node.js (server.js) —
fora do escopo desta religação de banco de dados. Placeholder honesto
em vez de quebrar a navegação.
"""

from __future__ import annotations

from flask import Blueprint, render_template

from core.auth import login_required

whatsapp_bp = Blueprint("whatsapp", __name__)
conferencia_bp = Blueprint("conferencia", __name__)


@whatsapp_bp.route("/whatsapp")
@login_required
def monitor_whatsapp():
    return render_template(
        "pendente_v2.html",
        titulo="Monitor WhatsApp",
        motivo="Esta funcionalidade depende do processo server.js (bot WhatsApp) "
               "e ainda não foi religada para o schema novo.",
    )


@conferencia_bp.route("/conferencia")
@login_required
def painel():
    from repositories_v2.monitoramento_repository import MonitoramentoRepository
    from models_v2.unidade import Unidade
    from extensions import db

    unidade = db.session.query(Unidade).order_by(Unidade.id).first()
    online, total = (0, 0)
    if unidade:
        online, total = MonitoramentoRepository().contar_cameras_online(unidade.id)

    return render_template("conferencia_v2/painel.html", online=online, total=total)
