"""
reset_dashboard.py — Backup + reset de rondas/alertas para testar do zero.

Monta seu PRÓPRIO Flask app mínimo (não importa app.py), usando a mesma
classe de config (config.get_config()) — assim pega a DATABASE_URL certa
sem disparar blueprints, logging customizado ou o conferencia_loop.

Uso:
    python reset_dashboard.py            # faz backup e pede confirmação antes de apagar
    python reset_dashboard.py --sem-backup   # pula o backup (não recomendado)
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask
from sqlalchemy import text

from extensions import db
from config import get_config

# App Flask "descartável" — só pra ter conexão com o banco.
# Não importa app.py, então nada de blueprints, logging customizado
# ou conferencia_loop é iniciado.
app = Flask(__name__)
app.config.from_object(get_config())
db.init_app(app)


def _serializar(row) -> dict:
    """Converte uma linha do banco (Row/objeto) em dict serializável em JSON."""
    d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def fazer_backup(pasta: Path) -> Path:
    """Exporta rondas, rondas_nvr e alertas para um único JSON antes de apagar."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"backup_reset_{datetime.now():%Y%m%d_%H%M%S}.json"

    with app.app_context():
        dados = {}
        for tabela in ("rondas", "rondas_nvr", "alertas"):
            rows = db.session.execute(text(f"SELECT * FROM {tabela}")).fetchall()
            dados[tabela] = [_serializar(r) for r in rows]
            print(f"  {tabela}: {len(rows)} linha(s) salvas no backup")

    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"✅ Backup salvo em: {caminho}")
    return caminho


def resetar():
    """Apaga alertas, rondas_nvr e rondas, e reinicia as sequências de ID."""
    with app.app_context():
        with db.session.begin():
            r1 = db.session.execute(text("DELETE FROM alertas"))
            r2 = db.session.execute(text("DELETE FROM rondas_nvr"))
            r3 = db.session.execute(text("DELETE FROM rondas"))

            for tabela in ("alertas", "rondas_nvr", "rondas"):
                seq = db.session.execute(
                    text("SELECT pg_get_serial_sequence(:t, 'id')"),
                    {"t": tabela},
                ).scalar()
                if seq:
                    db.session.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))

        print(f"🗑️  alertas: {r1.rowcount} apagada(s)")
        print(f"🗑️  rondas_nvr: {r2.rowcount} apagada(s)")
        print(f"🗑️  rondas: {r3.rowcount} apagada(s)")
        print("✅ Sequências de ID reiniciadas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sem-backup", action="store_true",
                         help="Pula o backup antes de apagar (não recomendado).")
    args = parser.parse_args()

    if not args.sem_backup:
        print("📦 Fazendo backup antes de apagar...")
        fazer_backup(Path("backups"))

    resposta = input(
        "\n⚠️  Isso vai APAGAR todos os dados de rondas, rondas_nvr e alertas. "
        "Digite CONFIRMAR para continuar: "
    )
    if resposta.strip() == "CONFIRMAR":
        resetar()
        print("\n✅ Reset concluído. Dashboard deve mostrar zero em tudo.")
    else:
        print("Operação cancelada. Nada foi apagado.")
