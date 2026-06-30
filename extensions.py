"""
extensions.py — Instâncias únicas das extensões Flask.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Instância global do SQLAlchemy — sem app vinculado ainda (padrão Application Factory)
db: SQLAlchemy = SQLAlchemy()

# Flask-Migrate gerencia as migrations Alembic
migrate: Migrate = Migrate()
