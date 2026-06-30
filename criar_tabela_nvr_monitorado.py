"""
Rodar UMA VEZ na raiz do projeto:
    python criar_tabela_nvr_monitorado.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from extensions import db
from models.nvr_monitorado import NvrMonitorado

with app.app_context():
    db.create_all()
    print("✅ Tabela nvr_monitorado criada (ou já existia).")
