"""
repositories_v2/base.py — Classe base para repositories do schema novo.

Duplica (deliberadamente, não importa) a lógica de repositories/base.py
— importar de lá disparia repositories/__init__.py (models antigos),
quebrando o isolamento explicado em repositories_v2/__init__.py.
Mesmo padrão de injeção de sessão, mesma justificativa (motor de ronda
roda em threads fora do contexto Flask).
"""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session


class BaseRepositoryV2:
    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        from extensions import db
        return db.session
