"""
routes/auth.py — Autenticação de monitores.

Substitui auth_routes.py.
Toda lógica de verificação de senha delegada ao MonitorRepository
via o método verificar_senha() do model Monitor.
Sem sqlite3, sem check_password_hash inline, sem get_db().
"""

from __future__ import annotations

from flask import (
    Blueprint, flash, redirect,
    render_template, request, session, url_for,
)

from core.auth import login_required
from repositories import MonitorRepository

auth_bp = Blueprint("auth", __name__)

_repo = MonitorRepository()


@auth_bp.route("/")
def index():
    if "monitor_id" in session:
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha   = request.form.get("senha", "")

        monitor = _repo.buscar_por_usuario(usuario)

        if monitor and monitor.verificar_senha(senha):
            session.clear()
            session["monitor_id"]    = monitor.id
            session["monitor_nome"]  = monitor.nome
            session["monitor_turno"] = monitor.turno
            flash(f"Bem-vindo, {monitor.nome}!", "success")
            return redirect(url_for("dashboard.dashboard"))

        flash("Usuário ou senha incorretos.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    response = redirect(url_for("auth.login"))
    response.set_cookie("session", "", expires=0)
    flash("Sessão encerrada.", "info")
    return response
