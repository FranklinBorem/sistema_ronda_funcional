"""
services_v2 — Serviços do schema reconstruído.

ISOLAMENTO DELIBERADO (mesmo padrão de models_v2/repositories_v2):
Pacote IRMÃO de services/, não subpasta — services/__init__.py já
importa RondaService/WhatsAppMonitorService/etc., que carregam os
models antigos. Ver models_v2/__init__.py para a explicação completa.

DUPLICAÇÃO TEMPORÁRIA E DELIBERADA (isapi_client.py):
A classe ISAPIClient aqui é uma cópia da classe já existente em
services/isapi_poller.py — não é possível importar de lá sem disparar
services/__init__.py (mesmo problema de isolamento). Como
services/isapi_poller.py ainda é usado pelas partes do sistema não
religadas (core/ronda_multi_nvr.py, services/conferencia_loop.py,
routes/conferencia_bp.py — Fases C/D), o arquivo original não pode
ser movido nem apagado ainda. Quando essas fases forem concluídas e
os chamadores antigos deixarem de existir, remover a duplicação
(arquivo antigo) vira um passo de limpeza explícito, não implícito.
"""
from .isapi_client import ISAPIClient, descobrir_canais
from .ronda_service import RondaService
from .conferencia_loop import iniciar_loop_v2

__all__ = ["ISAPIClient", "descobrir_canais", "RondaService", "iniciar_loop_v2"]
