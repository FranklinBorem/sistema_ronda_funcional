"""
repositories/__init__.py

Exporta todos os repositories para import direto.
"""

from .alerta_repository import AlertaRepository
from .mensagem_repository import MensagemRepository
from .monitor_repository import MonitorRepository
from .ronda_repository import RondaRepository

__all__ = [
    "AlertaRepository",
    "MensagemRepository",
    "MonitorRepository",
    "RondaRepository",
]
