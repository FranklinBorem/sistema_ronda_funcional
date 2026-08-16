"""
routes/conferencia_bp.py — Grupo Ronda · Conferência de Câmeras

Rotas de status (ISAPI polling):
  GET  /conferencia/                      → painel HTML
  GET  /conferencia/api/status            → polling de todos os NVRs ativos
  GET  /conferencia/api/status/<nvr_id>  → polling de um NVR específico
  GET  /conferencia/api/historico        → histórico da tabela nvr_status_log
  GET  /conferencia/api/eventos          → eventos de monitoramento
  GET  /conferencia/relatorio             → página de geração de relatório
  GET  /conferencia/relatorio/gerar       → gera e baixa relatório (pdf/xlsx)

O cadastro de NVRs (CRUD + importação CSV) vive em routes/nvr.py — este
blueprint só lê da tabela `nvrs` via models.nvr.Nvr, nunca escreve nela.
"""

import logging
from datetime import datetime

from flask import (
    Blueprint, jsonify, render_template,
    request, current_app, send_file,
)

from core.auth import login_required
from models.nvr import Nvr
from services.isapi_poller import (
    ConferenceManager,
    NvrConfig,
    NvrStatus,
)

logger = logging.getLogger(__name__)

conferencia_bp = Blueprint(
    "conferencia",
    __name__,
    url_prefix="/conferencia",
    template_folder="../templates",
    static_folder="../static",
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────────────────────

def _build_manager(nvr_ids: list[str] | None = None) -> ConferenceManager:
    """Constrói ConferenceManager a partir da tabela nvrs."""
    nvrs_db = Nvr.query.filter_by(ativo=True).all()

    if nvr_ids:
        nvrs_db = [n for n in nvrs_db if n.nvr_id in nvr_ids]

    if not nvrs_db:
        logger.warning("_build_manager: nenhum NVR ativo em nvrs")

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

    return ConferenceManager(
        nvr_configs,
        workers=current_app.config.get("ISAPI_WORKERS", 4),
        timeout=current_app.config.get("ISAPI_TIMEOUT", 8),
    )


def _serialize_nvr(nvr: NvrStatus) -> dict:
    return {
        "nvr_id":          nvr.nvr_id,
        "name":            nvr.name,
        "host":            nvr.host,
        "port":            nvr.port,
        "reachable":       nvr.reachable,
        "error":           nvr.error,
        "health":          nvr.health_label,
        "dev_status":      nvr.dev_status,
        "cameras_total":   nvr.cameras_total,
        "cameras_online":  nvr.cameras_online,
        "cameras_offline": nvr.cameras_offline,
        "polled_at":       nvr.polled_at.isoformat() if nvr.polled_at else None,
        "cameras": [
            {
                "id":            c.channel_id,
                "name":          c.channel_name or f"Canal {c.channel_id}",
                "online":        c.online,
                "signal_ok":     c.signal_ok,
                "recording":     c.recording,
                "record_status": c.record_status,
                "bit_rate_kbps": c.bit_rate_kbps,
                "ip":            c.ip_address,
                "model":         c.model,
                "raw_status":    c.raw_status,
            }
            for c in nvr.cameras
        ],
        "hdds": [
            {
                "id":            h.hdd_id,
                "status":        h.status,
                "status_label":  h.status_label,
                "capacity_mb":   h.capacity_mb,
                "free_space_mb": h.free_space_mb,
                "usage_pct":     h.usage_pct,
                "enabled":       h.enabled,
            }
            for h in nvr.hdds
        ],
    }


def _build_summary(results: list[NvrStatus]) -> dict:
    return {
        "nvrs_total":        len(results),
        "nvrs_ok":           sum(1 for n in results if n.health_label == "OK"),
        "nvrs_atencao":      sum(1 for n in results if n.health_label == "ATENÇÃO"),
        "nvrs_inacessiveis": sum(1 for n in results if not n.reachable),
        "cameras_total":     sum(n.cameras_total  for n in results),
        "cameras_online":    sum(n.cameras_online  for n in results),
        "cameras_offline":   sum(n.cameras_offline for n in results),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Painel
# ──────────────────────────────────────────────────────────────────────────────

@conferencia_bp.route("/")
@login_required
def painel():
    return render_template("conferencia/painel.html")


# ──────────────────────────────────────────────────────────────────────────────
# API de status (ISAPI polling)
# ──────────────────────────────────────────────────────────────────────────────

@conferencia_bp.route("/api/status")
@login_required
def api_status():
    try:
        nvr_ids_param = request.args.get("nvrs", "").strip()
        nvr_ids = [x.strip() for x in nvr_ids_param.split(",") if x.strip()] or None

        manager = _build_manager(nvr_ids)
        results = manager.poll_all()

        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "nvrs":      [_serialize_nvr(n) for n in results],
            "summary":   _build_summary(results),
        })
    except Exception:
        logger.exception("Erro em api_status")
        return jsonify({"error": "Erro interno no polling"}), 500


@conferencia_bp.route("/api/status/<nvr_id>")
@login_required
def api_status_nvr(nvr_id: str):
    try:
        nvr_db = Nvr.query.filter_by(nvr_id=nvr_id, ativo=True).first()
        if nvr_db is None:
            return jsonify({"error": f"NVR '{nvr_id}' não encontrado ou inativo"}), 404

        cfg = NvrConfig(
            nvr_id   = nvr_db.nvr_id,
            name     = nvr_db.nome,
            host     = nvr_db.ip,
            port     = nvr_db.porta,
            username = nvr_db.usuario,
            password = nvr_db.senha,
            use_https= nvr_db.use_https,
        )
        manager = ConferenceManager(
            [cfg], workers=1,
            timeout=current_app.config.get("ISAPI_TIMEOUT", 8),
        )
        results = manager.poll_all()
        return jsonify(_serialize_nvr(results[0]))
    except Exception:
        logger.exception(f"Erro em api_status_nvr({nvr_id})")
        return jsonify({"error": "Erro interno no polling"}), 500


# ──────────────────────────────────────────────────────────────────────────────
# API de histórico e eventos
# ──────────────────────────────────────────────────────────────────────────────

@conferencia_bp.route("/api/historico")
@login_required
def api_historico():
    from datetime import timedelta
    from models.nvr_status_log import NvrStatusLog

    nvr_id = request.args.get("nvr_id")
    horas  = int(request.args.get("horas", 24))
    desde  = datetime.utcnow() - timedelta(hours=horas)

    query = NvrStatusLog.query.filter(NvrStatusLog.timestamp >= desde)
    if nvr_id:
        query = query.filter_by(nvr_id=nvr_id)

    registros = query.order_by(NvrStatusLog.timestamp.desc()).limit(500).all()
    return jsonify({"registros": [r.to_dict() for r in registros]})


@conferencia_bp.route("/api/eventos")
@login_required
def api_eventos():
    from models.monitoring import MonitorEvent

    apenas_ativos = request.args.get("ativos", "1") != "0"
    query = MonitorEvent.query
    if apenas_ativos:
        query = query.filter_by(resolvido_em=None)

    eventos = query.order_by(MonitorEvent.aberto_em.desc()).limit(200).all()
    return jsonify({"eventos": [e.to_dict() for e in eventos]})


# ──────────────────────────────────────────────────────────────────────────────
# Relatório de Monitoramento
# ──────────────────────────────────────────────────────────────────────────────

@conferencia_bp.route("/relatorio")
@login_required
def relatorio():
    """Página de geração de relatório por período."""
    return render_template("conferencia/relatorio.html")


@conferencia_bp.route("/relatorio/gerar")
@login_required
def relatorio_gerar():
    """
    GET /conferencia/relatorio/gerar?dt_inicio=YYYY-MM-DDTHH:MM&dt_fim=YYYY-MM-DDTHH:MM&fmt=pdf|xlsx
    Gera e retorna o relatório como download.
    """
    import io as _io
    from services.relatorio_conferencia import gerar_relatorio

    try:
        dt_inicio_str = request.args.get("dt_inicio", "").strip()
        dt_fim_str    = request.args.get("dt_fim", "").strip()
        fmt           = request.args.get("fmt", "pdf").lower()

        if not dt_inicio_str or not dt_fim_str:
            return jsonify({"error": "dt_inicio e dt_fim são obrigatórios"}), 400

        dt_inicio = datetime.strptime(dt_inicio_str, "%Y-%m-%dT%H:%M")
        dt_fim    = datetime.strptime(dt_fim_str,    "%Y-%m-%dT%H:%M")

        if dt_fim <= dt_inicio:
            return jsonify({"error": "dt_fim deve ser maior que dt_inicio"}), 400

        if (dt_fim - dt_inicio).days > 31:
            return jsonify({"error": "Período máximo: 31 dias"}), 400

        if fmt not in ("pdf", "xlsx"):
            fmt = "pdf"

        conteudo = gerar_relatorio(dt_inicio, dt_fim, fmt=fmt)

        nome = (
            f"relatorio_monitoramento_"
            f"{dt_inicio.strftime('%Y%m%d_%H%M')}_{dt_fim.strftime('%Y%m%d_%H%M')}"
            f".{fmt}"
        )
        mime = (
            "application/pdf" if fmt == "pdf"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        return send_file(
            _io.BytesIO(conteudo),
            mimetype=mime,
            as_attachment=True,
            download_name=nome,
        )

    except ValueError as e:
        return jsonify({"error": f"Formato de data inválido: {e}"}), 400
    except Exception:
        logger.exception("Erro ao gerar relatório")
        return jsonify({"error": "Erro interno ao gerar relatório"}), 500
