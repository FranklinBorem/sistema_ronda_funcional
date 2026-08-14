"""
routes/auth.py — Autenticação de usuários (schema novo).

Usa UsuarioRepository/models_v2.Usuario. As CHAVES de sessão
("monitor_id", "monitor_nome", "monitor_turno") foram mantidas
intactas de propósito — dezenas de templates e rotas (dashboard.html,
base.html, routes/rondas.py, routes/alarmes.py, etc.) leem essas
chaves, e core/auth.py:login_required só verifica a presença de
"monitor_id" na sessão, sem se importar com o que ele representa.
Trocar os nomes das chaves exigiria tocar em toda essa superfície
nesta mesma etapa — fora de escopo da Fase A (religação de auth).

"monitor_turno" não existe mais como conceito no schema novo (não há
campo `turno` em Usuario) — fica vazio até (se) esse conceito for
reintroduzido como campo real.
"""

from __future__ import annotations

from flask import (
    Blueprint, flash, redirect,
    render_template, request, session, url_for,
)

from core.auth import login_required
from repositories_v2.usuario_repository import UsuarioRepository

auth_bp = Blueprint("auth", __name__)

_repo = UsuarioRepository()


@auth_bp.route("/")
def index():
    if "monitor_id" in session:
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario_login = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")

        usuario = _repo.buscar_por_login(usuario_login)

        if usuario and usuario.status == "ativo" and usuario.verificar_senha(senha):
            session.clear()
            session["monitor_id"] = usuario.id
            session["monitor_nome"] = usuario.nome
            session["monitor_turno"] = ""
            session["empresa_id"] = usuario.empresa_id
            session["papel"] = usuario.papel
            flash(f"Bem-vindo, {usuario.nome}!", "success")
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

