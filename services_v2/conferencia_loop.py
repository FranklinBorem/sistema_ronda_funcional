"""
services_v2/conferencia_loop.py — Loop de coleta de disponibilidade
(schema novo, Fase D da religação).

Substitui services/conferencia_loop.py. Roda em thread daemon,
consultando ISAPI (services_v2.isapi_client) para cada Nvr ativo com
endereco_ip preenchido, e persiste em NvrStatusLog/CameraStatusLog +
sincroniza Ocorrencia de falha por câmera (repositories_v2.
monitoramento_repository).

ESCOPO REDUZIDO frente ao poller antigo, deliberadamente: não replica
parsing de firmware/modelo de dispositivo nem status detalhado de
HD/CPU (services/isapi_poller.py:CameraConferencePoller fazia isso) —
o essencial para disponibilidade (NVR alcançável + canal online/
offline) está coberto; o resto pode ser adicionado depois se
necessário, sem exigir mudança de schema.

NÃO VALIDADO CONTRA HARDWARE REAL — mesma ressalva das Fases
anteriores. Testado com ISAPIClient mockado.
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 300  # 5 minutos, igual ao loop antigo


def _executar_ciclo_v2() -> None:
    """Um ciclo completo de polling para todos os Nvrs ativos com IP."""
    from repositories_v2.db_session import session_scope
    from repositories_v2.nvr_repository import NvrRepository
    from repositories_v2.monitoramento_repository import MonitoramentoRepository
    from services_v2.isapi_client import ISAPIClient
    from services_v2.notificacao_service import NotificacaoService

    with session_scope() as session:
        nvr_repo = NvrRepository(session=session)
        mon_repo = MonitoramentoRepository(session=session)
        notif_service = NotificacaoService(session=session)

        from models_v2.nvr import Nvr
        nvrs_com_ip = (
            session.query(Nvr)
            .filter(Nvr.status == "ativo")
            .filter(Nvr.endereco_ip.isnot(None))
            .all()
        )

        if not nvrs_com_ip:
            logger.debug("conferencia_loop v2: nenhum NVR ativo com IP para consultar")
            return

        for nvr in nvrs_com_ip:
            t0 = time.monotonic()
            try:
                client = ISAPIClient(
                    host=nvr.endereco_ip, port=nvr.porta or 80,
                    username=nvr.usuario_acesso or "", password=nvr.credencial_ref or "",
                )
                alcancavel = client.ping()
                latencia_ms = int((time.monotonic() - t0) * 1000)
                mon_repo.registrar_status_nvr(nvr.id, online=alcancavel, latencia_ms=latencia_ms)

                if not alcancavel:
                    for camera in nvr_repo.listar_cameras(nvr.id):
                        if camera.modo_conexao == "ip_direto":
                            # câmera avulsa é independente do NVR pai —
                            # verifica sua própria alcançabilidade, não
                            # herda a falha do NVR (essa é justamente a
                            # vantagem de ser "ip_direto").
                            try:
                                cam_client = ISAPIClient(
                                    host=camera.endereco_ip, port=camera.porta or 80,
                                    username=camera.usuario_acesso or "",
                                    password=camera.credencial_ref or "",
                                )
                                online_cam = cam_client.ping()
                            except Exception:
                                online_cam = False
                        else:
                            online_cam = False
                        mon_repo.registrar_status_camera(camera.id, online=online_cam)
                        ocorrencia, resolucao = mon_repo.sincronizar_ocorrencia_falha_camera(
                            camera.id, online=online_cam
                        )
                        if ocorrencia is not None:
                            notif_service.notificar_ocorrencia(ocorrencia, resolucao=resolucao)
                    continue

                try:
                    chan_data = client.get_chan_status()
                    chan_list = chan_data.get("ChanStatusList", chan_data).get("ChanStatus", [])
                    if isinstance(chan_list, dict):
                        chan_list = [chan_list]
                    status_por_canal = {
                        int(c.get("id", c.get("channel", 0))): str(c.get("online", "false")).lower() == "true"
                        for c in chan_list
                    }
                except Exception as e:
                    logger.warning("chanStatus falhou para NVR %s: %s", nvr.nome, e)
                    status_por_canal = {}

                for camera in nvr_repo.listar_cameras(nvr.id):
                    if camera.modo_conexao == "via_nvr":
                        online_cam = status_por_canal.get(camera.canal, alcancavel)
                    else:
                        # câmera avulsa: sua própria alcançabilidade, não a do NVR pai
                        try:
                            cam_client = ISAPIClient(
                                host=camera.endereco_ip, port=camera.porta or 80,
                                username=camera.usuario_acesso or "",
                                password=camera.credencial_ref or "",
                            )
                            online_cam = cam_client.ping()
                        except Exception:
                            online_cam = False
                    mon_repo.registrar_status_camera(camera.id, online=online_cam)
                    ocorrencia, resolucao = mon_repo.sincronizar_ocorrencia_falha_camera(
                        camera.id, online=online_cam
                    )
                    if ocorrencia is not None:
                        notif_service.notificar_ocorrencia(ocorrencia, resolucao=resolucao)

            except Exception as e:
                logger.error("Falha ao consultar NVR %s (%s): %s", nvr.nome, nvr.endereco_ip, e)
                mon_repo.registrar_status_nvr(nvr.id, online=False)


def _loop(intervalo_segundos: int) -> None:
    while True:
        try:
            _executar_ciclo_v2()
        except Exception as e:
            logger.error("conferencia_loop v2: ciclo falhou: %s", e)
        time.sleep(intervalo_segundos)


def iniciar_loop_v2(intervalo_segundos: int = INTERVALO_SEGUNDOS) -> threading.Thread:
    """Inicia a thread daemon. Chamar uma única vez, no startup do app."""
    thread = threading.Thread(target=_loop, args=(intervalo_segundos,), daemon=True)
    thread.start()
    return thread
