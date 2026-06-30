"""
services/conferencia_loop.py — Grupo Ronda · Loop de coleta de status

Roda em background (thread daemon) e salva no banco a cada INTERVALO_SEGUNDOS.
Popula três tabelas:
  - nvr_status_log      → uma linha por NVR por polling
  - camera_status_log   → uma linha por câmera por polling
  - monitor_event       → abre/fecha eventos de falha automaticamente

Inicialização em app.py:
    from services.conferencia_loop import iniciar_loop
    iniciar_loop(app)
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 300   # 5 minutos — ajuste conforme necessário


def _executar_polling(app):
    """Executa um ciclo completo de polling e salva no banco."""
    from extensions import db
    from models.nvr_monitorado import NvrMonitorado
    from models.nvr_status_log import NvrStatusLog
    from models.monitoring import CameraStatusLog, MonitorEvent
    from services.isapi_poller import ConferenceManager, NvrConfig

    with app.app_context():
        try:
            nvrs_db = NvrMonitorado.query.filter_by(ativo=True).all()
            if not nvrs_db:
                logger.debug("conferencia_loop: nenhum NVR ativo para pollar")
                return

            configs = [
                NvrConfig(
                    nvr_id=n.nvr_id, name=n.nome, host=n.ip,
                    port=n.porta, username=n.usuario,
                    password=n.senha, use_https=n.use_https,
                )
                for n in nvrs_db
            ]

            manager = ConferenceManager(configs, workers=4, timeout=10)
            results = manager.poll_all()
            agora = datetime.utcnow()

            for nvr in results:
                # ── 1. NvrStatusLog ────────────────────────────────────────
                log = NvrStatusLog(
                    nvr_id=nvr.nvr_id,
                    nvr_nome=nvr.name,
                    timestamp=agora,
                    health=nvr.health_label,
                    reachable=nvr.reachable,
                    cameras_total=nvr.cameras_total,
                    cameras_online=nvr.cameras_online,
                    cameras_offline=nvr.cameras_offline,
                    erro=nvr.error or None,
                )
                db.session.add(log)

                # ── 2. CameraStatusLog ─────────────────────────────────────
                for cam in nvr.cameras:
                    db.session.add(CameraStatusLog(
                        nvr_id=nvr.nvr_id,
                        channel_id=cam.channel_id,
                        channel_name=cam.channel_name or f"Canal {cam.channel_id}",
                        timestamp=agora,
                        online=cam.online,
                        signal_ok=cam.signal_ok,
                        recording=cam.recording,
                        bit_rate_kbps=cam.bit_rate_kbps,
                    ))

                # ── 3. MonitorEvent — NVR inacessível ─────────────────────
                _gerenciar_evento_nvr(db, nvr, agora)

                # ── 4. MonitorEvent — câmeras offline ─────────────────────
                for cam in nvr.cameras:
                    _gerenciar_evento_camera(db, nvr.nvr_id, cam, agora)

            db.session.commit()
            logger.info(f"conferencia_loop: polling OK — {len(results)} NVR(s)")

        except Exception:
            logger.exception("conferencia_loop: erro durante polling")
            try:
                db.session.rollback()
            except Exception:
                pass


def _gerenciar_evento_nvr(db, nvr, agora: datetime):
    """Abre ou fecha evento de NVR inacessível/em atenção."""
    from models.monitoring import MonitorEvent

    chave = "nvr_inacessivel" if not nvr.reachable else "nvr_atencao"
    ha_problema = not nvr.reachable or nvr.health_label == "ATENÇÃO"

    # Evento ativo existente para este NVR
    evento_ativo = MonitorEvent.query.filter_by(
        nvr_id=nvr.nvr_id,
        alvo_tipo="nvr",
        resolvido_em=None,
    ).first()

    if ha_problema:
        if not evento_ativo:
            db.session.add(MonitorEvent(
                alvo_tipo="nvr",
                nvr_id=nvr.nvr_id,
                nome_exibicao=nvr.name,
                severidade="critica" if not nvr.reachable else "media",
                chave_problema=chave,
                mensagem=f"NVR '{nvr.name}' {nvr.health_label}. {nvr.error or ''}".strip(),
                aberto_em=agora,
            ))
    else:
        if evento_ativo:
            evento_ativo.resolvido_em = agora


def _gerenciar_evento_camera(db, nvr_id: str, cam, agora: datetime):
    """Abre ou fecha evento de câmera offline."""
    from models.monitoring import MonitorEvent

    if not cam.online:
        evento = MonitorEvent.query.filter_by(
            nvr_id=nvr_id,
            channel_id=cam.channel_id,
            alvo_tipo="camera",
            resolvido_em=None,
        ).first()
        if not evento:
            db.session.add(MonitorEvent(
                alvo_tipo="camera",
                nvr_id=nvr_id,
                channel_id=cam.channel_id,
                nome_exibicao=cam.channel_name or f"Canal {cam.channel_id}",
                severidade="alta",
                chave_problema="camera_offline",
                mensagem=f"Câmera '{cam.channel_name}' offline (canal {cam.channel_id})",
                aberto_em=agora,
            ))
    else:
        # Fecha evento se estava aberto
        evento = MonitorEvent.query.filter_by(
            nvr_id=nvr_id,
            channel_id=cam.channel_id,
            alvo_tipo="camera",
            resolvido_em=None,
        ).first()
        if evento:
            evento.resolvido_em = agora


def _loop(app):
    """Thread principal do loop."""
    logger.info(f"conferencia_loop: iniciado (intervalo={INTERVALO_SEGUNDOS}s)")
    while True:
        _executar_polling(app)
        time.sleep(INTERVALO_SEGUNDOS)


def iniciar_loop(app):
    """
    Inicia o loop de coleta em thread daemon.
    Chamar UMA VEZ em app.py após create_app().

    Exemplo:
        from services.conferencia_loop import iniciar_loop
        iniciar_loop(app)
    """
    t = threading.Thread(target=_loop, args=(app,), daemon=True, name="conferencia_loop")
    t.start()
    logger.info("conferencia_loop: thread daemon iniciada")
