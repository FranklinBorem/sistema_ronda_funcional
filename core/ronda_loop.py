"""
core/ronda_loop.py — Motor de Ronda Contínua.

Executa rondas em sequência, uma após a outra, até receber sinal de parada.

Mudanças em relação à versão SQLite:
  - _criar_ronda_pai() → RondaRepository.criar() via session_scope()
  Toda operação de banco usa session_scope() — seguro para threads.

Integração com Flask:
    from core.ronda_loop import iniciar_loop, parar_loop, status_loop
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.ronda_multi_nvr import executar_ronda_multi

# =========================================================
# ESTADO GLOBAL (thread-safe via Lock)
# =========================================================

_lock   = threading.Lock()
_thread: Optional[threading.Thread] = None

_estado = {
    "ativo":           False,
    "parar":           False,
    "ciclo_atual":     0,
    "total_ciclos":    0,
    "iniciado_em":     None,
    "ultimo_ciclo":    None,
    "monitor_nome":    "",
    "monitor_id":      None,
    "turno":           "",
    "nvr_ids":         None,
    "log":             [],
    "ultimo_ronda_id": None,
    "ultimo_pasta":    None,
    "erro":            None,
}

MAX_LOG = 100


def _log(msg: str, nivel: str = "INFO") -> None:
    ts   = datetime.now().strftime("%H:%M:%S")
    linha = f"[{ts}] [{nivel}] {msg}"
    logging.getLogger("ronda_loop").log(
        logging.INFO if nivel == "INFO" else logging.WARNING, msg
    )
    with _lock:
        _estado["log"].append(linha)
        if len(_estado["log"]) > MAX_LOG:
            _estado["log"] = _estado["log"][-MAX_LOG:]


# =========================================================
# BANCO — cria ronda pai via repository
# =========================================================

def _criar_ronda_pai(
    monitor_id: int,
    monitor_nome: str,
    turno: str,
    pasta: str,
) -> Optional[int]:
    """
    Insere ronda pai usando RondaRepository + session_scope().
    Substitui _criar_ronda_pai() com sqlite3 direto.
    Retorna o ID gerado ou None em caso de falha.
    """
    try:
        from repositories.db_session import session_scope
        from repositories.ronda_repository import RondaRepository
        with session_scope() as session:
            ronda = RondaRepository(session=session).criar(
                monitor_id=monitor_id,
                monitor_nome=monitor_nome,
                turno=turno,
                pasta=pasta,
            )
            return ronda.id
    except Exception as e:
        _log(f"Erro ao criar ronda no banco: {e}", "WARN")
        return None


# =========================================================
# WORKER — roda em thread separada
# =========================================================

def _worker(
    monitor_id: int,
    monitor_nome: str,
    turno: str,
    nvr_ids: Optional[list],
) -> None:
    _log(f"=== LOOP DE RONDA INICIADO | Monitor: {monitor_nome} | Turno: {turno} ===")

    with _lock:
        _estado["ativo"]        = True
        _estado["parar"]        = False
        _estado["ciclo_atual"]  = 0
        _estado["total_ciclos"] = 0
        _estado["iniciado_em"]  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _estado["ultimo_ciclo"] = None
        _estado["erro"]         = None

    try:
        while True:
            with _lock:
                deve_parar = _estado["parar"]
            if deve_parar:
                _log("Sinal de parada recebido. Encerrando após ciclo atual.")
                break

            with _lock:
                _estado["ciclo_atual"] += 1
                ciclo = _estado["ciclo_atual"]

            _log(f"--- Iniciando ciclo #{ciclo} ---")

            ts    = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            pasta = str(Path("relatorios") / f"loop_{ts}_ciclo{ciclo:03d}")

            ronda_id = _criar_ronda_pai(monitor_id, monitor_nome, turno, pasta)

            with _lock:
                _estado["ultimo_ronda_id"] = ronda_id
                _estado["ultimo_pasta"]    = pasta

            try:
                executar_ronda_multi(
                    monitor_nome=monitor_nome,
                    turno=turno,
                    pasta=pasta,
                    ronda_id=ronda_id,
                    nvr_ids=nvr_ids,
                )
                with _lock:
                    _estado["total_ciclos"] += 1
                    _estado["ultimo_ciclo"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _log(f"Ciclo #{ciclo} concluído. Total: {_estado['total_ciclos']}")

            except Exception as e:
                _log(f"Erro no ciclo #{ciclo}: {e}", "WARN")
                with _lock:
                    _estado["erro"] = str(e)
                continue

            with _lock:
                deve_parar = _estado["parar"]
            if deve_parar:
                _log("Sinal de parada recebido. Loop encerrado após ciclo concluído.")
                break

    except Exception as e:
        _log(f"Erro crítico no loop: {e}", "WARN")
        with _lock:
            _estado["erro"] = str(e)
    finally:
        with _lock:
            _estado["ativo"]       = False
            _estado["ciclo_atual"] = 0
        _log("=== LOOP DE RONDA ENCERRADO ===")


# =========================================================
# API PÚBLICA
# =========================================================

def iniciar_loop(
    monitor_id: int,
    monitor_nome: str,
    turno: str,
    nvr_ids: Optional[list] = None,
) -> dict:
    """
    Inicia o loop de ronda contínua em background.
    Retorna {"ok": True} ou {"erro": "motivo"}.
    """
    global _thread

    with _lock:
        if _estado["ativo"]:
            return {"erro": "Loop já está em execução."}

        _estado["monitor_id"]   = monitor_id
        _estado["monitor_nome"] = monitor_nome
        _estado["turno"]        = turno
        _estado["nvr_ids"]      = nvr_ids
        _estado["log"]          = []

    _thread = threading.Thread(
        target=_worker,
        args=(monitor_id, monitor_nome, turno, nvr_ids),
        daemon=True,
        name="ronda-loop",
    )
    _thread.start()
    return {"ok": True}


def parar_loop() -> dict:
    """
    Sinaliza parada. A ronda em curso termina normalmente;
    nenhuma nova é iniciada após a conclusão.
    """
    with _lock:
        if not _estado["ativo"]:
            return {"erro": "Loop não está em execução."}
        _estado["parar"] = True

    _log("Parada solicitada. Aguardando fim do ciclo atual...")
    return {"ok": True}


def status_loop() -> dict:
    """Retorna snapshot do estado atual do loop."""
    with _lock:
        return {
            "ativo":           _estado["ativo"],
            "parar":           _estado["parar"],
            "ciclo_atual":     _estado["ciclo_atual"],
            "total_ciclos":    _estado["total_ciclos"],
            "iniciado_em":     _estado["iniciado_em"],
            "ultimo_ciclo":    _estado["ultimo_ciclo"],
            "monitor_nome":    _estado["monitor_nome"],
            "turno":           _estado["turno"],
            "ultimo_ronda_id": _estado["ultimo_ronda_id"],
            "ultimo_pasta":    _estado["ultimo_pasta"],
            "erro":            _estado["erro"],
            "log":             list(_estado["log"][-20:]),
        }
