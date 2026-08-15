"""
repositories_v2/db_session.py — Sessão SQLAlchemy fora do Flask context.

Duplica (deliberadamente) repositories/db_session.py — mesmo motivo de
isolamento dos outros arquivos deste pacote: importar de
repositories/db_session.py dispararia repositories/__init__.py
(models antigos). O conteúdo é pequeno e não tem nenhuma dependência
de model, então a duplicação é trivial de manter sincronizada se um
dia for necessário.

Uso exclusivo do motor de ronda (core/ronda_multi_nvr.py,
core/ronda_loop.py) rodando em threads sem Flask request context.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

_engine: Engine | None = None


def init_engine(engine: Engine) -> None:
    global _engine
    _engine = engine


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    if _engine is None:
        raise RuntimeError(
            "session_scope() (v2) chamado antes de init_engine(). "
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
