"""
models/__init__.py

Exporta todos os models para registro no SQLAlchemy.
"""
from .alerta import Alerta
from .mensagem import Mensagem, StatusSistema
from .monitor import Monitor
from .monitoring import CameraStatusLog, MonitorEvent
from .nvr import Nvr, NvrPreset
from .nvr_status_log import NvrStatusLog
from .ronda import Ronda


__all__ = [
    "Alerta",
    "CameraStatusLog",
    "Mensagem",
    "Monitor",
    "MonitorEvent",
    "Nvr",
    "NvrPreset",
    "NvrStatusLog",
    "Ronda",
    "StatusSistema",
]
