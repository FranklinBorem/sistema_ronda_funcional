"""
repositories/monitor_repository.py — Acesso a dados de monitores.

Substitui as queries diretas de core.py e auth_routes.py.
"""

from __future__ import annotations

from typing import Optional

from models.monitor import Monitor
from .base import BaseRepository


class MonitorRepository(BaseRepository):

    def buscar_por_usuario(self, usuario: str) -> Optional[Monitor]:
        """Retorna o monitor pelo username ou None. Usado no login."""
        return (
            self.session
            .query(Monitor)
            .filter_by(usuario=usuario)
            .first()
        )

    def buscar_por_id(self, monitor_id: int) -> Optional[Monitor]:
        return self.session.get(Monitor, monitor_id)

    def listar_todos(self) -> list[Monitor]:
        return (
            self.session
            .query(Monitor)
            .order_by(Monitor.nome)
            .all()
        )

    def listar_nomes(self) -> list[str]:
        """Retorna lista de nomes — usado em filtros de e-mail/dashboard."""
        rows = (
            self.session
            .query(Monitor.nome)
            .distinct()
            .order_by(Monitor.nome)
            .all()
        )
        return [r.nome for r in rows]

    def criar(
        self,
        nome: str,
        usuario: str,
        senha_plain: str,
        turno: str,
    ) -> Monitor:
        """
        Cria e persiste um novo monitor.
        Lança sqlalchemy.exc.IntegrityError se o usuário já existir.
        """
        monitor = Monitor(nome=nome, usuario=usuario, turno=turno)
        monitor.set_senha(senha_plain)
        self.session.add(monitor)
        self.session.flush()   # gera o ID sem fechar a transação
        return monitor

    def existe_usuario(self, usuario: str) -> bool:
        return (
            self.session
            .query(Monitor.id)
            .filter_by(usuario=usuario)
            .first()
        ) is not None
