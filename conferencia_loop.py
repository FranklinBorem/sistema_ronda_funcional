"""
conferencia_loop.py — "Zabbix Server" caseiro do Grupo Ronda.

Roda em loop infinito, independente de qualquer navegador estar aberto.
A cada INTERVALO_SEGUNDOS:
  1. Consulta todos os NVRs ativos via ISAPI (NVR + câmeras individuais)
  2. Grava histórico em camera_status_log e nvr_status_log (time series)
  3. Avalia triggers (MonitorEngineService) e abre/fecha eventos
  4. Notifica por e-mail E/OU Discord os eventos novos

Uso:
    python conferencia_loop.py
    python conferencia_loop.py --intervalo 60
    python conferencia_loop.py --intervalo 120 --sem-email
"""

from __future__ import annotations

import argparse
import logging
import time

from app import create_app
from extensions import db
from models.nvr_monitorado import NvrMonitorado           # ← modelo correto
from services.isapi_poller import ConferenceManager, NvrConfig
from services.monitor_engine_service import MonitorEngineService
from services.monitor_notification_service import MonitorNotificationService
from services.discord_notification_service import (
    DiscordNotificationService,
    make_discord_service_from_app,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("conferencia_loop")


# ──────────────────────────────────────────────────────────────────────────
# Montagem do ConferenceManager a partir do banco
# ──────────────────────────────────────────────────────────────────────────

def _montar_manager(app) -> ConferenceManager:
    """Lê NvrMonitorado ativos e monta o manager de polling."""
    nvrs_db = NvrMonitorado.query.filter_by(ativo=True).all()
    if not nvrs_db:
        logger.warning("Nenhum NVR ativo em nvr_monitorado — nada a monitorar.")

    nvr_configs = [
        NvrConfig(
            nvr_id   = n.nvr_id,
            name     = n.nome,
            host     = n.ip,
            port     = n.porta,
            username = n.usuario,
            password = n.senha,
            use_https= n.use_https,
        )
        for n in nvrs_db
    ]
    timeout = app.config.get("ISAPI_TIMEOUT", 8)
    workers = app.config.get("ISAPI_WORKERS", 4)
    return ConferenceManager(nvr_configs, workers=workers, timeout=timeout)


# ──────────────────────────────────────────────────────────────────────────
# Loop principal
# ──────────────────────────────────────────────────────────────────────────

def main(intervalo_segundos: int, com_email: bool, com_discord: bool) -> None:
    app    = create_app()
    engine = MonitorEngineService()

    # Notificadores (instanciados fora do loop, dentro do app_context)
    with app.app_context():
        email_svc   = MonitorNotificationService() if com_email else None
        discord_svc = make_discord_service_from_app(app) if com_discord else None

        # Teste de conectividade do Discord na inicialização
        if discord_svc and discord_svc.enabled and discord_svc.webhook_url:
            logger.info("Testando webhook Discord...")
            ok = discord_svc.enviar_teste()
            logger.info("Discord webhook: OK" if ok else "Discord webhook: FALHOU — verifique DISCORD_WEBHOOK_URL")

    logger.info(
        f"Iniciando monitoramento contínuo "
        f"(intervalo={intervalo_segundos}s | e-mail={'sim' if com_email else 'não'} | "
        f"discord={'sim' if com_discord else 'não'})"
    )

    with app.app_context():
        while True:
            try:
                manager    = _montar_manager(app)
                resultados = manager.poll_all()

                # Avalia triggers — grava histórico + abre/fecha eventos
                novos_eventos = engine.processar(resultados)

                # Notifica eventos novos
                if novos_eventos:
                    if email_svc:
                        email_svc.notificar_novos_eventos(novos_eventos)
                    if discord_svc:
                        discord_svc.notificar_novos_eventos(novos_eventos)
                    db.session.commit()   # persiste notificado=True

                # Notifica resoluções (eventos que fecharam neste ciclo)
                # MonitorEngineService.processar fecha eventos mas não os retorna separadamente;
                # para notificar resoluções, use a extensão abaixo (opcional).
                # _notificar_resolucoes(engine, email_svc, discord_svc)

                # Log de ciclo
                ok          = sum(1 for r in resultados if r.health_label == "OK")
                atencao     = sum(1 for r in resultados if r.health_label == "ATENÇÃO")
                inacessivel = sum(1 for r in resultados if not r.reachable)
                logger.info(
                    f"Ciclo concluído — {len(resultados)} NVR(s): "
                    f"OK={ok}  ATENÇÃO={atencao}  INACESSÍVEL={inacessivel}  "
                    f"| novos eventos={len(novos_eventos)}"
                )

            except Exception:
                logger.exception("Erro inesperado no ciclo de monitoramento")

            time.sleep(intervalo_segundos)


# ──────────────────────────────────────────────────────────────────────────
# Entrada de linha de comando
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Monitoramento contínuo de NVRs/câmeras via ISAPI · Grupo Ronda"
    )
    parser.add_argument(
        "--intervalo", type=int, default=120,
        help="Intervalo entre ciclos (segundos). Padrão: 120",
    )
    parser.add_argument(
        "--sem-email", action="store_true",
        help="Desativa notificações por e-mail mesmo que MAIL_* estejam configurados.",
    )
    parser.add_argument(
        "--sem-discord", action="store_true",
        help="Desativa notificações Discord mesmo que DISCORD_WEBHOOK_URL esteja configurado.",
    )
    args = parser.parse_args()

    main(
        intervalo_segundos=args.intervalo,
        com_email=not args.sem_email,
        com_discord=not args.sem_discord,
    )


# ──────────────────────────────────────────────────────────────────────────
# Como manter rodando no Windows
# ──────────────────────────────────────────────────────────────────────────
# Task Scheduler (simples):
#   Programa : ...\venv312\Scripts\python.exe
#   Argumentos: conferencia_loop.py --intervalo 120
#   Disparador: Ao iniciar o computador
#   Marcar    : "Executar com privilégios mais altos" + "estando o usuário
#                conectado ou não"
#
# NSSM (robusto — reinicia se cair):
#   nssm install ConferenciaRondaMonitor "C:\...\venv312\Scripts\python.exe"
#   nssm set ConferenciaRondaMonitor AppParameters "conferencia_loop.py --intervalo 120"
#   nssm set ConferenciaRondaMonitor AppDirectory "C:\caminho\do\projeto"
#   nssm start ConferenciaRondaMonitor
