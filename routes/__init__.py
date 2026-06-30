"""
routes/__init__.py — Registro central de blueprints.
"""

from __future__ import annotations
from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .auth import auth_bp
    from .alarmes import alarmes_bp
    from .conferencia_bp import conferencia_bp
    from .dashboard import dashboard_bp
    from .email import email_bp
    from .nvr import nvr_bp
    from .ronda_loop import ronda_loop_bp
    from .rondas import rondas_bp
    from .whatsapp import whatsapp_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(rondas_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(alarmes_bp)
    app.register_blueprint(ronda_loop_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(nvr_bp)
    app.register_blueprint(conferencia_bp)