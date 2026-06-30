"""
migrations/criar_nvr_monitorado.py
Cria a tabela nvr_monitorado no banco PostgreSQL do Grupo Ronda.

Executar UMA VEZ:
    python migrations/criar_nvr_monitorado.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app, db
from models.nvr_monitorado import NvrMonitorado

with app.app_context():
    db.create_all()          # cria somente tabelas que ainda não existem
    print("✅ Tabela nvr_monitorado criada (ou já existia).")

    # Opcional: insere um NVR de exemplo para testar
    if not NvrMonitorado.query.first():
        exemplo = NvrMonitorado(
            nvr_id   = "nvr_exemplo",
            nome     = "NVR Exemplo — Apagar após teste",
            site     = "Teste",
            ip       = "192.168.1.100",
            porta    = 80,
            usuario  = "admin",
            senha    = "senha123",
            ativo    = False,   # inativo por padrão
        )
        db.session.add(exemplo)
        db.session.commit()
        print("📌 NVR de exemplo inserido (ativo=False).")
