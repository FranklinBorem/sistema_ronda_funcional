"""
seed.py — Inicializa o banco de dados e cria o monitor administrador.

Execute UMA VEZ após a migração para PostgreSQL:
    python seed.py

O script:
  1. Cria todas as tabelas mapeadas pelo SQLAlchemy (db.create_all)
  2. Verifica se o usuário 'admin' já existe (idempotente)
  3. Insere o monitor admin com senha hasheada via werkzeug

Após rodar, acesse o sistema com:
    Usuário : admin
    Senha   : admin123

Troque a senha pelo painel assim que fizer o primeiro login.
"""

from __future__ import annotations

import sys

# ── Importa a factory do app ───────────────────────────────────────────────
# Ajuste o import abaixo se sua factory tiver outro nome/local.
# Exemplos comuns:
#   from app import create_app          ← mais comum
#   from app import app as create_app  ← se não usar factory
try:
    from app import create_app
except ImportError:
    print("[ERRO] Não foi possível importar 'create_app' de app.py.")
    print("       Ajuste o import no topo deste arquivo conforme seu projeto.")
    sys.exit(1)

from extensions import db
from models.monitor import Monitor


# ── Configurações do admin inicial ─────────────────────────────────────────
ADMIN_NOME    = "Administrador"
ADMIN_USUARIO = "admin"
ADMIN_SENHA   = "admin123"          # Troque após o primeiro login!
ADMIN_TURNO   = "Administrativo"


def criar_tabelas(app) -> None:
    """Cria todas as tabelas no PostgreSQL via SQLAlchemy ORM."""
    with app.app_context():
        db.create_all()
        print("[OK] Tabelas criadas (ou já existentes).")


def inserir_admin(app) -> None:
    """Insere o monitor admin se ainda não existir."""
    with app.app_context():
        existente = Monitor.query.filter_by(usuario=ADMIN_USUARIO).first()

        if existente:
            print(f"[AVISO] Usuário '{ADMIN_USUARIO}' já existe — nenhuma alteração feita.")
            return

        admin = Monitor(
            nome    = ADMIN_NOME,
            usuario = ADMIN_USUARIO,
            turno   = ADMIN_TURNO,
        )
        admin.set_senha(ADMIN_SENHA)   # gera hash werkzeug, igual ao sistema

        db.session.add(admin)
        db.session.commit()

        print(f"[OK] Monitor admin criado com sucesso.")
        print(f"     Usuário : {ADMIN_USUARIO}")
        print(f"     Senha   : {ADMIN_SENHA}")
        print(f"     Turno   : {ADMIN_TURNO}")
        print()
        print("[!]  Troque a senha pelo painel após o primeiro login!")


if __name__ == "__main__":
    app = create_app()

    print("=== Vigilante IA — Seed do banco de dados ===")
    print()

    criar_tabelas(app)
    inserir_admin(app)

    print()
    print("=== Concluído ===")
