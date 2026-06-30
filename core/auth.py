"""
core/auth.py — Decorator de autenticação.

Extraído de core.py para que as rotas possam importá-lo
sem depender do core.py original (que acessa sqlite3 diretamente).
"""

from __future__ import annotations

from functools import wraps

from flask import flash, jsonify, redirect, request, session, url_for


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "monitor_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"erro": "não autenticado"}), 401
            flash("Faça login para continuar.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated
