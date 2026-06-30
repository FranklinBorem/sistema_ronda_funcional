"""
limpar_rondas.py — Apaga todas as rondas e alertas, mantendo PTZs e monitores.

Execute UMA VEZ:
    python limpar_rondas.py

Tabelas afetadas (truncate em cascata):
  - alertas
  - ronda_nvrs  (filhos de rondas)
  - rondas
"""

from __future__ import annotations
import sys

try:
    from app import create_app
except ImportError:
    print("[ERRO] Não foi possível importar create_app de app.py.")
    sys.exit(1)

from extensions import db


def limpar(app):
    with app.app_context():
        print("Tabelas que serão limpas: alertas, ronda_nvrs, rondas")
        confirma = input("Confirmar? (s/N): ").strip().lower()
        if confirma != "s":
            print("Cancelado.")
            return

        # TRUNCATE com RESTART IDENTITY zera os IDs também
        db.session.execute(db.text("TRUNCATE TABLE alertas RESTART IDENTITY CASCADE"))
        db.session.execute(db.text("TRUNCATE TABLE rondas RESTART IDENTITY CASCADE"))
        db.session.commit()

        print("[OK] Rondas e alertas apagados. PTZs e monitores mantidos.")


if __name__ == "__main__":
    limpar(create_app())
