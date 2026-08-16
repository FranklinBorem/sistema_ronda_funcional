"""
services_v2/ronda_service.py — Orquestração de rondas (schema novo).

Substitui services/ronda_service.py no schema reconstruído. Já nasce
com a correção do bug crítico original (RondaService.iniciar_ronda_multi
apontava para um script inexistente via subprocess.Popen — ver
docs anteriores/plano de correção): dispara core.ronda_multi_nvr.
executar_ronda_multi_v2() diretamente em uma thread daemon, no mesmo
padrão já usado (e validado) por core/ronda_loop.py para a ronda
contínua.

NÃO VALIDADO CONTRA HARDWARE REAL — ver core/ronda_multi_nvr.py,
seção "ORQUESTRAÇÃO — SCHEMA NOVO" para o que foi e não foi testado.
"""

from __future__ import annotations

import threading

from repositories_v2.ronda_repository import RondaRepository


class RondaService:
    """Orquestra criação e disparo de rondas (câmeras PTZ de uma Unidade)."""

    def __init__(self, ronda_repo: RondaRepository | None = None) -> None:
        self._ronda_repo = ronda_repo or RondaRepository()

    def iniciar_ronda_multi(
        self,
        unidade_id: int,
        usuario_id: int | None,
        monitor_nome: str = "Não informado",
        turno: str = "Não informado",
    ) -> int:
        """
        Cria o registro de Ronda (status='em_andamento') e dispara a
        execução em background. Retorna o ID da ronda imediatamente —
        quem chama consulta o status depois (GET /api/ronda/<id>).
        """
        ronda = self._ronda_repo.criar(unidade_id=unidade_id, usuario_id=usuario_id)

        from extensions import db
        db.session.commit()

        thread = threading.Thread(
            target=self._executar_em_background,
            args=(unidade_id, monitor_nome, turno, ronda.id),
            daemon=True,
        )
        thread.start()

        return ronda.id

    @staticmethod
    def _executar_em_background(
        unidade_id: int, monitor_nome: str, turno: str, ronda_id: int
    ) -> None:
        """
        Roda em thread separada, fora do contexto Flask — por isso usa
        session_scope() (repositories_v2.db_session), não db.session.
        Qualquer exceção aqui é capturada e registrada como falha da
        ronda, nunca propagada silenciosamente (thread morta sem
        deixar rastro seria pior que uma ronda marcada como 'erro').
        """
        from core.ronda_multi_nvr import executar_ronda_multi_v2

        try:
            executar_ronda_multi_v2(
                unidade_id=unidade_id,
                monitor_nome=monitor_nome,
                turno=turno,
                ronda_id=ronda_id,
            )
        except Exception as e:
            try:
                from repositories_v2.db_session import session_scope
                from repositories_v2.ronda_repository import RondaRepository as _RR
                with session_scope() as session:
                    _RR(session=session).finalizar(ronda_id=ronda_id, status="erro")
            except Exception:
                pass  # não deixa uma falha ao registrar a falha derrubar a thread
            print(f"[RondaService v2] Ronda {ronda_id} falhou: {e}")
