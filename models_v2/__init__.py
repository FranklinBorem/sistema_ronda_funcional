"""
models_v2 — Schema reconstruído do produto (FASE -1/0, ver docs/database/modelo-banco.md).

IMPORTANTE — ISOLAMENTO DELIBERADO, E POR QUE FICA FORA DE models/:
Este pacote vive como IRMÃO de models/, não como subpasta dele.
Em Python, `import models.v2` executaria primeiro models/__init__.py
(que carrega os models antigos: Monitor, Nvr, NvrMonitorado, Ronda,
Alerta, MonitorEvent) e só depois o submódulo — causando colisão de
nome de tabela na mesma MetaData compartilhada (ex.: duas classes
diferentes mapeando "nvrs"). Como pacote de nível superior separado
(`import models_v2`), models/__init__.py nunca é executado junto,
então não há conflito, mesmo os dois lados usando a mesma instância
`db` de extensions.py.

A aplicação em produção (app.py -> import models) continua intocada
e usando exclusivamente o schema antigo até a etapa de "religar
routes/services/core para o novo schema" (fora do escopo desta
entrega) — quando isso acontecer, os arquivos deste pacote substituem
os antigos.
"""
from .empresa import Empresa
from .usuario import Usuario, UsuarioUnidade
from .unidade import Unidade, Area
from .nvr import Nvr, Camera, Preset
from .ronda import Ronda, ResultadoRonda
from .deteccao import RegraDeteccao, EventoIA
from .ocorrencia import Ocorrencia
from .notificacao import Notificacao, Integracao
from .auditoria import Auditoria
from .plano import Plano

__all__ = [
    "Empresa", "Usuario", "UsuarioUnidade", "Unidade", "Area",
    "Nvr", "Camera", "Preset", "Ronda", "ResultadoRonda",
    "RegraDeteccao", "EventoIA", "Ocorrencia", "Notificacao",
    "Integracao", "Auditoria", "Plano",
]
