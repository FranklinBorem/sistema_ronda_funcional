"""
migrar_alertas_subcategoria.py — Converte StatusAlerta.DETECCAO_FALSA em
TRATADO + motivo_tratamento='falso_positivo'. Idempotente.

Rodar DEPOIS de aplicar models/alerta.py, repositories/alerta_repository.py,
routes/alarmes.py e templates/alarmes.html, e DEPOIS de reiniciar o Flask
(para o SQLAlchemy já reconhecer a nova coluna motivo_tratamento).

Ajuste o import de create_app abaixo se o ponto de entrada do seu app
tiver outro nome/local (mesmo padrão usado em migrar_unificar_nvrs.py).
"""

from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    with db.engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE alertas ADD COLUMN IF NOT EXISTS motivo_tratamento VARCHAR(30)"
        ))

        result = conn.execute(text("""
            UPDATE alertas
            SET status = 'tratado', motivo_tratamento = 'falso_positivo'
            WHERE status = 'deteccao_falsa'
        """))
        print(f"Convertidos 'deteccao_falsa' -> 'tratado/falso_positivo': {result.rowcount}")

        result = conn.execute(text("""
            UPDATE alertas
            SET motivo_tratamento = 'confirmado'
            WHERE status = 'tratado' AND motivo_tratamento IS NULL
        """))
        print(f"Preenchidos com 'confirmado': {result.rowcount}")

print("Migração concluída.")
