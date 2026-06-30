"""
repositories/db_session.py — Sessão SQLAlchemy fora do Flask context.

Uso exclusivo do motor de ronda (ronda_multi_nvr.py, ronda_loop.py)
que roda em threads separadas, sem Flask request context.

Exemplo:
    from repositories.db_session import session_scope
    from repositories import AlertaRepository, RondaRepository

    with session_scope() as session:
        repo = AlertaRepository(session=session)
        repo.registrar(nvr_id=..., ...)
        # commit automático ao sair do bloco
        # rollback automático em caso de exceção
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# Engine global — preenchida por init_engine() no startup do app.
# Permite uso em threads sem depender do Flask application context.
_engine: Engine | None = None


def init_engine(engine: Engine) -> None:
    """
    Registra a engine SQLAlchemy para uso fora do Flask context.
    Deve ser chamado em app.py logo após db.init_app(app).

    Exemplo em _register_extensions() no app.py:
        from repositories.db_session import init_engine
        db.init_app(app)
        with app.app_context():
            init_engine(db.engine)
    """
    global _engine
    _engine = engine


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager que abre, comita ou reverte uma sessão SQLAlchemy
    sem depender do Flask application context.

    Requer que init_engine() já tenha sido chamado no startup do app.
    Pode ser chamado de qualquer thread após o app estar rodando.
    """
    if _engine is None:
        raise RuntimeError(
            "session_scope() chamado antes de init_engine(). "
            "Certifique-se de chamar init_engine(db.engine) no startup do app."
        )

    session = Session(_engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
