"""
repositories_v2/monitoramento_repository.py — Persistência de
disponibilidade (NvrStatusLog/CameraStatusLog) e gestão de Ocorrência
por falha de equipamento (origem='falha_equipamento').
"""

from __future__ import annotations

from datetime import datetime, timezone

from models_v2.monitoramento import NvrStatusLog, CameraStatusLog
from models_v2.ocorrencia import Ocorrencia
from models_v2.nvr import Nvr, Camera
from .base import BaseRepositoryV2


class MonitoramentoRepository(BaseRepositoryV2):

    # ── Log bruto de disponibilidade ────────────────────────────────────

    def registrar_status_nvr(
        self, nvr_id: int, online: bool, latencia_ms: int | None = None,
        detalhes: dict | None = None,
    ) -> NvrStatusLog:
        log = NvrStatusLog(nvr_id=nvr_id, online=online, latencia_ms=latencia_ms, detalhes=detalhes)
        self.session.add(log)
        self.session.flush()
        return log

    def registrar_status_camera(
        self, camera_id: int, online: bool, detalhes: dict | None = None,
    ) -> CameraStatusLog:
        log = CameraStatusLog(camera_id=camera_id, online=online, detalhes=detalhes)
        self.session.add(log)
        self.session.flush()
        return log

    # ── Ocorrência de falha (abre/fecha automaticamente) ─────────────────

    def sincronizar_ocorrencia_falha_camera(
        self, camera_id: int, online: bool
    ) -> tuple[Ocorrencia | None, bool]:
        """
        Se online=False e não há ocorrência de falha ABERTA para esta
        câmera, abre uma nova (origem='falha_equipamento'). Se
        online=True e existe uma ocorrência ABERTA, marca como
        resolvida. Idempotente — chamar a cada ciclo de polling não
        duplica ocorrências.

        Retorna (ocorrencia, resolucao) — ocorrencia é None quando
        nada mudou neste ciclo (nem abriu nem fechou); resolucao=True
        indica que a ocorrência retornada é um fechamento (para quem
        chama decidir se/como notificar).
        """
        aberta = (
            self.session.query(Ocorrencia)
            .filter_by(origem="falha_equipamento", status="aberta")
            .filter(Ocorrencia.tipo == f"camera:{camera_id}")
            .first()
        )

        if not online and aberta is None:
            camera = self.session.get(Camera, camera_id)
            if camera is None:
                return None, False
            nvr = camera.nvr
            unidade = nvr.unidade
            ocorrencia = Ocorrencia(
                empresa_id=unidade.empresa_id,
                unidade_id=unidade.id,
                origem="falha_equipamento",
                tipo=f"camera:{camera_id}",
                prioridade="alta",
                status="aberta",
            )
            self.session.add(ocorrencia)
            self.session.flush()
            return ocorrencia, False

        elif online and aberta is not None:
            aberta.status = "resolvida"
            aberta.tratado_em = datetime.now(timezone.utc)
            self.session.flush()
            return aberta, True

        return None, False

    def contar_cameras_online(self, unidade_id: int) -> tuple[int, int]:
        """(online, total) — última leitura de cada câmera da unidade."""
        from sqlalchemy import func

        subq = (
            self.session.query(
                CameraStatusLog.camera_id,
                func.max(CameraStatusLog.timestamp).label("ultimo"),
            )
            .join(Camera, Camera.id == CameraStatusLog.camera_id)
            .join(Nvr, Nvr.id == Camera.nvr_id)
            .filter(Nvr.unidade_id == unidade_id)
            .group_by(CameraStatusLog.camera_id)
            .subquery()
        )
        ultimos = (
            self.session.query(CameraStatusLog.online)
            .join(
                subq,
                (CameraStatusLog.camera_id == subq.c.camera_id)
                & (CameraStatusLog.timestamp == subq.c.ultimo),
            )
            .all()
        )
        total = len(ultimos)
        online = sum(1 for (o,) in ultimos if o)
        return online, total
