"""
repositories_v2 — Camada de acesso a dados do schema reconstruído.

ISOLAMENTO DELIBERADO (mesmo motivo de models_v2, ver seu __init__.py):
Vive como pacote IRMÃO de repositories/, não subpasta. O pacote
repositories/__init__.py já importa os repositories antigos, que por
sua vez importam models/__init__.py (schema antigo) — se este pacote
fosse repositories/v2/, `from repositories.v2.X import Y` executaria
repositories/__init__.py primeiro (carregando os models antigos) e
colidiria com models_v2 na mesma MetaData compartilhada.

Como pacote de nível superior separado, isso nunca acontece.
"""
from .base import BaseRepositoryV2
from .usuario_repository import UsuarioRepository
from .nvr_repository import NvrRepository
from .ronda_repository import RondaRepository
from .monitoramento_repository import MonitoramentoRepository

__all__ = [
    "BaseRepositoryV2", "UsuarioRepository", "NvrRepository",
    "RondaRepository", "MonitoramentoRepository",
]
