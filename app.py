"""
app.py — Application Factory do Vigilante IA.

Uso:
    # Produção (via PM2 / gunicorn):
    python app.py

    # Gunicorn:
    gunicorn "app:create_app()" -b 0.0.0.0:5000 -w 4

    # Flask CLI:
    flask --app app run --debug
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Configuração de logging
# Chamada antes de create_app() para que todos os módulos que fazem
# logging.getLogger(__name__) no import já herdem o handler correto.
# ──────────────────────────────────────────────────────────────────────────────

def _configure_logging() -> None:
    """
    Configura dois handlers:
      1. Console (StreamHandler)  — nível INFO, sempre ativo
      2. Arquivo rotativo         — nível DEBUG, rotaciona a cada 5 MB, mantém 5 backups

    O arquivo fica em logs/vigilante.log (criado automaticamente).
    O nível do logger raiz respeita FLASK_ENV:
      development → DEBUG (arquivo e console em DEBUG)
      production  → INFO  (arquivo em DEBUG, console em INFO)

    Módulos de terceiros ruidosos (requests, urllib3) ficam em WARNING.
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Handler 1: console ────────────────────────────────────────────────
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(logging.INFO)

    # ── Handler 2: arquivo rotativo ───────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "vigilante.log",
        maxBytes=5 * 1024 * 1024,   # 5 MB por arquivo
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    # ── Logger raiz ───────────────────────────────────────────────────────
    root = logging.getLogger()
    env = os.getenv("FLASK_ENV", "production")
    root.setLevel(logging.DEBUG if env == "development" else logging.INFO)
    root.addHandler(console)
    root.addHandler(file_handler)

    # ── Silencia libs ruidosas ────────────────────────────────────────────
    for noisy in ("urllib3", "requests", "werkzeug"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        f"Logging configurado — env={env} arquivo=logs/vigilante.log"
    )


_configure_logging()


# ──────────────────────────────────────────────────────────────────────────────
# Application Factory
# ──────────────────────────────────────────────────────────────────────────────

def create_app(config_override: dict | None = None) -> Flask:
    app = Flask(__name__)

    from config import get_config
    app.config.from_object(get_config())

    if config_override:
        app.config.update(config_override)

    _register_extensions(app)
    _register_blueprints(app)
    _register_hooks(app)

    return app


def _register_extensions(app: Flask) -> None:
    from extensions import db, migrate

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        import models  # noqa: F401

        from repositories.db_session import init_engine
        init_engine(db.engine)


def _register_blueprints(app: Flask) -> None:
    from routes import register_blueprints
    register_blueprints(app)


def _register_hooks(app: Flask) -> None:
    from extensions import db

    @app.before_request
    def _limpar_sessao_inicial():
        if not getattr(app, "_sessao_iniciada", False):
            from flask import session
            session.clear()
            app._sessao_iniciada = True  # type: ignore[attr-defined]

    @app.teardown_appcontext
    def _fechar_sessao_db(exc: BaseException | None = None) -> None:
        db.session.remove()


def _seed_admin(app: Flask) -> None:
    from extensions import db
    from models.monitor import Monitor

    with app.app_context():
        if not Monitor.query.filter_by(usuario="admin").first():
            admin = Monitor(
                nome="Administrador",
                usuario="admin",
                turno="Administrativo",
            )
            admin.set_senha("admin123")
            db.session.add(admin)
            db.session.commit()
            logging.getLogger(__name__).info("Usuário padrão criado: admin / admin123")


def _criar_tabelas(app: Flask) -> None:
    from extensions import db
    with app.app_context():
        db.create_all()
        logging.getLogger(__name__).info("Tabelas verificadas/criadas.")


# ── Entry point direto ────────────────────────────────────────────────────────

app = create_app()

# ── Loop de coleta de status (Conferência de Câmeras) ────────────────────────
# Roda em thread daemon: salva NvrStatusLog, CameraStatusLog e MonitorEvent
# a cada 5 minutos automaticamente.
from services.conferencia_loop import iniciar_loop
iniciar_loop(app)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _criar_tabelas(app)
    _seed_admin(app)
    app.run(
        debug=os.getenv("FLASK_ENV", "production") == "development",
        use_reloader=False,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
    )
