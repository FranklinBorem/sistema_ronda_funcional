"""
routes/__init__.py — Registro central de blueprints (schema novo).

CORTE FINAL da religação (ver Fases A-E nos commits anteriores):
todos os blueprints aqui já usam models_v2/repositories_v2/
services_v2. Os blueprints antigos (routes/nvr.py, routes/rondas.py,
routes/alarmes.py, routes/conferencia_bp.py, routes/dashboard.py,
routes/whatsapp.py, routes/email.py, routes/ronda_loop.py) não são
mais registrados aqui — continuam no repositório para referência
histórica (ver git log desta função), mas não fazem parte do
processo em execução a partir deste commit.

routes/whatsapp.py (bridge com o bot Node.js) e routes/email.py
ainda NÃO têm equivalente v2 completo — routes/pendentes_v2.py
registra um placeholder para /whatsapp que informa isso claramente
em vez de quebrar a navegação (ver base.html). E-mail não tem rota
de UI ainda; a integração de notificação por e-mail em si é trabalho
futuro (fora do escopo desta religação de banco de dados).

routes/ronda_loop.py (ronda contínua/agendada) também não foi
religado — a funcionalidade de ronda manual (routes/rondas_v2.py)
está completa e testada; a ronda contínua fica para uma iteração
futura.
"""

from __future__ import annotations
from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .auth import auth_bp
    from .dashboard_v2 import dashboard_bp
    from .equipamentos import equipamentos_bp
    from .rondas_v2 import rondas_v2_bp
    from .ocorrencias import ocorrencias_bp
    from .pendentes_v2 import whatsapp_bp, conferencia_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(equipamentos_bp)
    app.register_blueprint(rondas_v2_bp)
    app.register_blueprint(ocorrencias_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(conferencia_bp)