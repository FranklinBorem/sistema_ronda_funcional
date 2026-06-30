"""
services/monitor_engine_service.py — Motor de avaliação estilo "Triggers" do Zabbix.

Recebe o resultado de um polling (NvrStatus, com suas CameraStatus) e decide:
  - Quais condições de problema estão ativas agora (NVR inacessível,
    NVR em atenção, câmera offline, câmera sem sinal)
  - Abre um MonitorEvent quando uma condição passa a existir
  - Fecha (resolve) o MonitorEvent quando a condição deixa de existir
  - Sinaliza quais eventos são "novos" (para quem chamar disparar notificação)

Mantém o estado de "o que já está aberto" consultando o próprio banco,
então funciona corretamente mesmo se o processo for reiniciado.
"""

from __future__ import annotations

from datetime import datetime

from extensions import db
from models.monitoring import CameraStatusLog, MonitorEvent
from models.nvr_status_log import NvrStatusLog
from services.isapi_poller import NvrStatus

# Severidade por tipo de problema — ajuste livremente conforme sua operação.
SEVERIDADE = {
    "nvr_inacessivel": "critica",
    "nvr_atencao": "media",
    "camera_offline": "alta",
    "camera_sem_sinal": "media",
}


class MonitorEngineService:
    """Avalia um ciclo de polling e mantém o estado de eventos no banco."""

    def processar(self, resultados: list[NvrStatus]) -> list[MonitorEvent]:
        """
        Processa uma lista de NvrStatus (resultado de ConferenceManager.poll_all).
        Grava histórico (NVR + câmeras) e atualiza eventos.
        Retorna a lista de eventos NOVOS abertos neste ciclo (para notificação).
        """
        novos_eventos: list[MonitorEvent] = []

        for nvr in resultados:
            self._gravar_historico_nvr(nvr)
            novos_eventos += self._avaliar_nvr(nvr)

            for cam in nvr.cameras:
                self._gravar_historico_camera(nvr.nvr_id, cam)
                novos_eventos += self._avaliar_camera(nvr, cam)

        db.session.commit()
        return novos_eventos

    # ── Histórico ────────────────────────────────────────────────────────────

    def _gravar_historico_nvr(self, nvr: NvrStatus) -> None:
        db.session.add(NvrStatusLog(
            nvr_id=nvr.nvr_id,
            nvr_nome=nvr.name,
            timestamp=nvr.polled_at or datetime.utcnow(),
            health=nvr.health_label,
            reachable=nvr.reachable,
            cameras_total=nvr.cameras_total,
            cameras_online=nvr.cameras_online,
            cameras_offline=nvr.cameras_offline,
            erro=nvr.error or None,
        ))

    def _gravar_historico_camera(self, nvr_id: str, cam) -> None:
        db.session.add(CameraStatusLog(
            nvr_id=nvr_id,
            channel_id=cam.channel_id,
            channel_name=cam.channel_name or f"Canal {cam.channel_id}",
            online=cam.online,
            signal_ok=cam.signal_ok,
            recording=cam.recording,
            bit_rate_kbps=cam.bit_rate_kbps,
        ))

    # ── Avaliação NVR ────────────────────────────────────────────────────────

    def _avaliar_nvr(self, nvr: NvrStatus) -> list[MonitorEvent]:
        novos = []

        if not nvr.reachable:
            novos += self._abrir_se_necessario(
                alvo_tipo="nvr", nvr_id=nvr.nvr_id, channel_id=None,
                chave="nvr_inacessivel", nome=nvr.name,
                mensagem=f"NVR '{nvr.name}' inacessível. {nvr.error or ''}".strip(),
            )
            # Se está inacessível, não faz sentido também ter "atenção" aberto por baixo
            self._resolver_se_aberto(nvr.nvr_id, None, "nvr_atencao")
        else:
            self._resolver_se_aberto(nvr.nvr_id, None, "nvr_inacessivel")

            if nvr.cameras_offline > 0 or nvr.dev_status != 0:
                novos += self._abrir_se_necessario(
                    alvo_tipo="nvr", nvr_id=nvr.nvr_id, channel_id=None,
                    chave="nvr_atencao", nome=nvr.name,
                    mensagem=(
                        f"NVR '{nvr.name}' em atenção: "
                        f"{nvr.cameras_offline} câmera(s) offline, dev_status={nvr.dev_status}."
                    ),
                )
            else:
                self._resolver_se_aberto(nvr.nvr_id, None, "nvr_atencao")

        return novos

    # ── Avaliação Câmera ─────────────────────────────────────────────────────

    def _avaliar_camera(self, nvr: NvrStatus, cam) -> list[MonitorEvent]:
        novos = []
        nome_cam = f"{nvr.name} / {cam.channel_name or f'Canal {cam.channel_id}'}"

        # Se o NVR está inacessível, não cravamos problema de câmera
        # individual (seria ruído: não sabemos o estado real dela).
        if not nvr.reachable:
            return novos

        if not cam.online:
            novos += self._abrir_se_necessario(
                alvo_tipo="camera", nvr_id=nvr.nvr_id, channel_id=cam.channel_id,
                chave="camera_offline", nome=nome_cam,
                mensagem=f"Câmera '{nome_cam}' está offline.",
            )
        else:
            self._resolver_se_aberto(nvr.nvr_id, cam.channel_id, "camera_offline")

            if not cam.signal_ok:
                novos += self._abrir_se_necessario(
                    alvo_tipo="camera", nvr_id=nvr.nvr_id, channel_id=cam.channel_id,
                    chave="camera_sem_sinal", nome=nome_cam,
                    mensagem=f"Câmera '{nome_cam}' está online porém sem sinal de vídeo.",
                )
            else:
                self._resolver_se_aberto(nvr.nvr_id, cam.channel_id, "camera_sem_sinal")

        return novos

    # ── Internos: abrir/resolver evento (idempotente) ───────────────────────

    def _abrir_se_necessario(
        self, alvo_tipo: str, nvr_id: str, channel_id: int | None,
        chave: str, nome: str, mensagem: str,
    ) -> list[MonitorEvent]:
        existente = self._buscar_evento_aberto(nvr_id, channel_id, chave)
        if existente:
            return []  # já está aberto, não duplica

        evento = MonitorEvent(
            alvo_tipo=alvo_tipo,
            nvr_id=nvr_id,
            channel_id=channel_id,
            nome_exibicao=nome,
            severidade=SEVERIDADE.get(chave, "media"),
            chave_problema=chave,
            mensagem=mensagem,
        )
        db.session.add(evento)
        db.session.flush()  # garante evento.id antes de retornar
        return [evento]

    def _resolver_se_aberto(self, nvr_id: str, channel_id: int | None, chave: str) -> None:
        existente = self._buscar_evento_aberto(nvr_id, channel_id, chave)
        if existente:
            existente.resolvido_em = datetime.utcnow()

    def _buscar_evento_aberto(
        self, nvr_id: str, channel_id: int | None, chave: str,
    ) -> MonitorEvent | None:
        query = MonitorEvent.query.filter_by(
            nvr_id=nvr_id, chave_problema=chave, resolvido_em=None,
        )
        if channel_id is None:
            query = query.filter(MonitorEvent.channel_id.is_(None))
        else:
            query = query.filter_by(channel_id=channel_id)
        return query.first()
