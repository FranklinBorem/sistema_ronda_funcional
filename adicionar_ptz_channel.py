"""
adicionar_ptz_channel.py — Migration manual para adicionar as colunas
ptz_channel e snapshot_channel na tabela nvrs.

Por que manual em vez de `flask db migrate`?
Porque o autogenerate do Alembic pode capturar outras alteracoes
pendentes do modelo que voce ainda nao revisou. Este script faz
EXATAMENTE uma coisa: adiciona as duas colunas com valores padrao
seguros, sem tocar em mais nada.

Uso:
    python adicionar_ptz_channel.py

Pode ser executado quantas vezes quiser — usa IF NOT EXISTS,
entao e seguro rodar de novo sem duplicar colunas.
"""

from app import create_app
from extensions import db

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(db.text("""
            ALTER TABLE nvrs
            ADD COLUMN IF NOT EXISTS ptz_channel INTEGER NOT NULL DEFAULT 1;
        """))
        conn.execute(db.text("""
            ALTER TABLE nvrs
            ADD COLUMN IF NOT EXISTS snapshot_channel VARCHAR(20) NOT NULL DEFAULT '501';
        """))
        conn.commit()

    print("[OK] Colunas ptz_channel e snapshot_channel adicionadas/verificadas na tabela nvrs.")
    print()
    print("Valores atuais por NVR (revise se o canal 1 / '501' esta correto para cada um):")
    from models.nvr import Nvr
    for nvr in Nvr.query.order_by(Nvr.site, Nvr.nome).all():
        print(f"  {nvr.nvr_id:20s} site={nvr.site or '-':15s} "
              f"ptz_channel={nvr.ptz_channel}  snapshot_channel={nvr.snapshot_channel}")
