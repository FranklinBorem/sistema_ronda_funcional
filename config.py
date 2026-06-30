"""
config.py — Configuração centralizada por ambiente.

Uso no app.py:
    app.config.from_object(get_config())

Variáveis de ambiente obrigatórias em produção:
    DATABASE_URL   — postgresql+psycopg2://user:pass@host:5432/dbname
    SECRET_KEY     — string aleatória longa

Variáveis opcionais:
    FLASK_ENV      — "development" | "production" | "testing"  (default: production)
    SQLALCHEMY_POOL_SIZE        (default: 5)
    SQLALCHEMY_MAX_OVERFLOW     (default: 10)
    SQLALCHEMY_POOL_TIMEOUT     (default: 30)
    SQLALCHEMY_POOL_RECYCLE     (default: 1800)
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class BaseConfig:
    # ── Segurança ──────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_hex(32))
    SESSION_PERMANENT: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # ── SQLAlchemy ─────────────────────────────────────────────────────────
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_RECORD_QUERIES: bool = False

    # Pool (válido para PostgreSQL; ignorado pelo SQLite)
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_size":    int(os.getenv("SQLALCHEMY_POOL_SIZE", 5)),
        "max_overflow": int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", 10)),
        "pool_timeout": int(os.getenv("SQLALCHEMY_POOL_TIMEOUT", 30)),
        "pool_recycle": int(os.getenv("SQLALCHEMY_POOL_RECYCLE", 1800)),
        "pool_pre_ping": True,   # reconecta automaticamente após idle
    }

    # ── Relatórios ─────────────────────────────────────────────────────────
    RELATORIOS_DIR: Path = BASE_DIR / "relatorios"

    # ── SMTP ───────────────────────────────────────────────────────────────
    SMTP_HOST: str      = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int      = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str      = os.getenv("SMTP_USER", "")
    SMTP_PASS: str      = os.getenv("SMTP_PASS", "")
    SMTP_TLS: bool      = os.getenv("SMTP_TLS", "1") == "1"
    SMTP_REMETENTE: str = os.getenv("SMTP_REMETENTE", os.getenv("SMTP_USER", ""))

# ── Discord ────────────────────────────────────────────────────────────
    DISCORD_WEBHOOK_URL:     str  = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1520976634218287155/QNDrNhBrciw3NEe_AgefFnu3OkBCIawMXdj8HpSbUIfCIumhnoQFK_T8c4xweFnaXO7b")
    DISCORD_WEBHOOK_ENABLED: bool = True
    DISCORD_MENTION_ROLE_ID: str  = os.getenv("DISCORD_MENTION_ROLE_ID", "")

class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True
    SQLALCHEMY_RECORD_QUERIES: bool = True

    # SQLite como fallback para dev local sem Postgres
    _sqlite_url = f"sqlite:///{BASE_DIR / 'database.db'}"
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", _sqlite_url)

    # Pool menor para SQLite (não usa pool real)
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        **BaseConfig.SQLALCHEMY_ENGINE_OPTIONS,
        "pool_size": 1,
        "max_overflow": 0,
    }


class ProductionConfig(BaseConfig):
    DEBUG: bool = False

    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL",
        # Fallback explícito — vai falhar ruidosamente se não configurado,
        # o que é o comportamento correto em produção.
        "postgresql+psycopg2://postgres:postgres@localhost:5432/vigilante_ia",
    )

    # Cookies seguros em HTTPS
    SESSION_COOKIE_SECURE: bool = True


class TestingConfig(BaseConfig):
    TESTING: bool = True
    WTF_CSRF_ENABLED: bool = False

    # Banco em memória para testes — isolado por sessão
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", "sqlite:///:memory:"
    )
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_size": 1,
        "max_overflow": 0,
    }


# ── Mapa de ambientes ──────────────────────────────────────────────────────
_CONFIG_MAP: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
}


def get_config() -> type[BaseConfig]:
    """
    Retorna a classe de configuração correta baseada em FLASK_ENV.
    Default: ProductionConfig (fail-safe).
    """
    env = os.getenv("FLASK_ENV", "production").lower()
    return _CONFIG_MAP.get(env, ProductionConfig)
