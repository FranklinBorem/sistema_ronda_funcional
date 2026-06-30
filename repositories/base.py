"""
repositories/base.py — Classe base para todos os repositories.

Por que injetar sessão em vez de usar db.session diretamente?
──────────────────────────────────────────────────────────────
O motor de ronda (ronda_multi_nvr.py) roda em threads separadas, fora
do Flask request context. Se o repository chamasse `db.session`
diretamente, a thread não teria contexto e levantaria RuntimeError.

Com injeção de sessão:
  • Dentro do Flask (routes/services): não passa nada → usa db.session
  • Fora do Flask (threads do motor): passa uma Session do SQLAlchemy

Uso:
    # Dentro de uma rota Flask (session gerenciada pelo teardown)
    repo = AlertaRepository()
    repo.listar(status="pendente")

    # Dentro de uma thread do motor de ronda
    from sqlalchemy.orm import Session
    from extensions import db
    with db.engine.connect() as conn:
        with Session(bind=conn) as session:
            repo = AlertaRepository(session=session)
            repo.registrar(...)
"""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session


class BaseRepository:
    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        """
        Retorna a sessão injetada ou, se não houver, a sessão do
        contexto Flask atual (db.session é um proxy thread-local).
        """
        if self._session is not None:
            return self._session
        from extensions import db
        return db.session
