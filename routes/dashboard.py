"""
routes/dashboard.py — Dashboard principal.

Substitui dashboard_routes.py.
A rota apenas lê o parâmetro `dias` e delega tudo ao DashboardService.
"""

from __future__ import annotations

from flask import Blueprint, render_template, request

from core.auth import login_required
from services import DashboardService

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    dias = int(request.args.get("dias", 30))
    context = DashboardService(dias=dias).build_context()
    return render_template("dashboard.html", **context)
