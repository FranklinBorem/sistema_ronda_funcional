"""
routes/conferencia_bp.py — Grupo Ronda · Conferência de Câmeras

Rotas de status (ISAPI polling):
  GET  /conferencia/                      → painel HTML
  GET  /conferencia/api/status            → polling de todos os NVRs ativos
  GET  /conferencia/api/status/<nvr_id>  → polling de um NVR específico
  GET  /conferencia/api/historico        → histórico da tabela nvr_status_log
  GET  /conferencia/api/eventos          → eventos de monitoramento

Rotas de CRUD (tabela nvr_monitorado):
  GET  /conferencia/nvrs                  → lista NVRs monitorados
  GET  /conferencia/nvrs/novo             → formulário cadastro
  POST /conferencia/nvrs/novo             → salva novo NVR
  GET  /conferencia/nvrs/<nvr_id>/editar  → formulário edição
  POST /conferencia/nvrs/<nvr_id>/editar  → salva edição
  POST /conferencia/nvrs/<nvr_id>/toggle  → ativa/desativa
  POST /conferencia/nvrs/<nvr_id>/excluir → exclui

Rotas de importação em lote:
  GET  /conferencia/nvrs/importar         → página de upload CSV
  POST /conferencia/nvrs/importar         → processa CSV e cria NVRs
  GET  /conferencia/nvrs/importar/modelo  → baixa CSV modelo
"""

import csv
import io
import logging
from datetime import datetime

from flask import (
    Blueprint, Response, jsonify, render_template,
    request, current_app, redirect, url_for, flash, send_file,
)

from core.auth import login_required
from extensions import db
from models.nvr_monitorado import NvrMonitorado
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
    """Constrói ConferenceManager a partir da tabela nvr_monitorado."""
    nvrs_db = NvrMonitorado.query.filter_by(ativo=True).all()

    if nvr_ids:
        nvrs_db = [n for n in nvrs_db if n.nvr_id in nvr_ids]

    if not nvrs_db:
        logger.warning("_build_manager: nenhum NVR ativo em nvr_monitorado")

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
        nvr_db = NvrMonitorado.query.filter_by(nvr_id=nvr_id, ativo=True).first()
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
# CRUD de NVRs monitorados
# ──────────────────────────────────────────────────────────────────────────────

@conferencia_bp.route("/nvrs")
@login_required
def nvrs_listar():
    nvrs = NvrMonitorado.query.order_by(NvrMonitorado.nome).all()
    return render_template("conferencia/nvrs.html", nvrs=nvrs)


@conferencia_bp.route("/nvrs/novo", methods=["GET", "POST"])
@login_required
def nvrs_novo():
    if request.method == "POST":
        nvr = NvrMonitorado(
            nvr_id   = request.form["nvr_id"].strip(),
            nome     = request.form["nome"].strip(),
            site     = request.form.get("site", "").strip(),
            ip       = request.form["ip"].strip(),
            porta    = int(request.form.get("porta", 80)),
            use_https= "use_https" in request.form,
            usuario  = request.form.get("usuario", "admin").strip(),
            senha    = request.form["senha"],
            ativo    = "ativo" in request.form,
        )
        db.session.add(nvr)
        db.session.commit()
        flash(f'NVR "{nvr.nome}" cadastrado com sucesso.', "success")
        return redirect(url_for("conferencia.nvrs_listar"))

    return render_template("conferencia/nvr_form.html", nvr=None)


@conferencia_bp.route("/nvrs/<nvr_id>/editar", methods=["GET", "POST"])
@login_required
def nvrs_editar(nvr_id: str):
    nvr = NvrMonitorado.query.filter_by(nvr_id=nvr_id).first_or_404()

    if request.method == "POST":
        nvr.nome      = request.form["nome"].strip()
        nvr.site      = request.form.get("site", "").strip()
        nvr.ip        = request.form["ip"].strip()
        nvr.porta     = int(request.form.get("porta", 80))
        nvr.use_https = "use_https" in request.form
        nvr.usuario   = request.form.get("usuario", "admin").strip()
        nvr.ativo     = "ativo" in request.form
        senha = request.form.get("senha", "").strip()
        if senha:
            nvr.senha = senha
        db.session.commit()
        flash(f'NVR "{nvr.nome}" atualizado.', "success")
        return redirect(url_for("conferencia.nvrs_listar"))

    return render_template("conferencia/nvr_form.html", nvr=nvr)


@conferencia_bp.route("/nvrs/<nvr_id>/toggle", methods=["POST"])
@login_required
def nvrs_toggle(nvr_id: str):
    nvr = NvrMonitorado.query.filter_by(nvr_id=nvr_id).first_or_404()
    nvr.ativo = not nvr.ativo
    db.session.commit()
    estado = "ativado" if nvr.ativo else "desativado"
    flash(f'NVR "{nvr.nome}" {estado}.', "success")
    return redirect(url_for("conferencia.nvrs_listar"))


@conferencia_bp.route("/nvrs/<nvr_id>/excluir", methods=["POST"])
@login_required
def nvrs_excluir(nvr_id: str):
    nvr = NvrMonitorado.query.filter_by(nvr_id=nvr_id).first_or_404()
    nome = nvr.nome
    db.session.delete(nvr)
    db.session.commit()
    flash(f'NVR "{nome}" excluído.', "success")
    return redirect(url_for("conferencia.nvrs_listar"))


# ──────────────────────────────────────────────────────────────────────────────
# Importação em lote via CSV
# ──────────────────────────────────────────────────────────────────────────────

_TRUTHY = {"1", "true", "sim", "yes", "s", "y"}


def _parse_bool_csv(val: str) -> bool:
    return str(val).strip().lower() in _TRUTHY


def _parse_csv(texto: str) -> tuple[list[dict], list[str]]:
    """
    Lê CSV (separador ; ou ,) e retorna (linhas_válidas, erros).
    Aceita cabeçalho com ou sem BOM UTF-8 (gerado pelo Excel).
    Colunas esperadas:
      nvr_id | nome | site | ip | porta | usuario | senha | use_https | ativo
    """
    texto = texto.lstrip("\ufeff")   # remove BOM do Excel
    try:
        dialect = csv.Sniffer().sniff(texto[:512], delimiters=";,")
    except csv.Error:
        dialect = csv.excel  # fallback: vírgula padrão

    reader = csv.DictReader(io.StringIO(texto), dialect=dialect)

    # Normaliza nomes de colunas (espaços, acentos, maiúsculas)
    if reader.fieldnames:
        reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]

    linhas, erros = [], []
    for i, row in enumerate(reader, start=2):   # linha 1 = cabeçalho
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items()}

        nvr_id = row.get("nvr_id", "").replace(" ", "_")
        if not nvr_id:
            erros.append(f"Linha {i}: nvr_id vazio — ignorada.")
            continue

        ip = row.get("ip", "")
        if not ip:
            erros.append(f"Linha {i} ({nvr_id}): ip vazio — ignorada.")
            continue

        try:
            porta = int(row.get("porta") or 80)
        except ValueError:
            erros.append(f"Linha {i} ({nvr_id}): porta inválida — usando 80.")
            porta = 80

        linhas.append({
            "nvr_id":    nvr_id,
            "nome":      row.get("nome") or nvr_id,
            "site":      row.get("site", ""),
            "ip":        ip,
            "porta":     porta,
            "usuario":   row.get("usuario") or "admin",
            "senha":     row.get("senha", ""),
            "use_https": _parse_bool_csv(row.get("use_https", "0")),
            "ativo":     _parse_bool_csv(row.get("ativo", "1")),
        })

    return linhas, erros


@conferencia_bp.route("/nvrs/importar", methods=["GET", "POST"])
@login_required
def nvrs_importar():
    if request.method == "GET":
        return render_template("conferencia/nvrs_importar.html")

    # POST — processa arquivo enviado
    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename:
        flash("Nenhum arquivo enviado.", "warning")
        return redirect(url_for("conferencia.nvrs_importar"))

    # Tenta decodificar UTF-8 (com ou sem BOM) e cai em Latin-1 se falhar
    try:
        texto = arquivo.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            arquivo.seek(0)
            texto = arquivo.read().decode("latin-1")
        except Exception:
            flash("Não foi possível decodificar o arquivo. Use UTF-8 ou Latin-1.", "danger")
            return redirect(url_for("conferencia.nvrs_importar"))

    linhas, erros = _parse_csv(texto)

    criados, ignorados = [], []
    for d in linhas:
        existente = NvrMonitorado.query.filter_by(nvr_id=d["nvr_id"]).first()
        if existente:
            ignorados.append(d["nvr_id"])
            continue
        db.session.add(NvrMonitorado(**d))
        criados.append(d["nvr_id"])

    db.session.commit()

    if criados:
        flash(f"✅ {len(criados)} NVR(s) cadastrados: {', '.join(criados)}", "success")
    if ignorados:
        flash(f"⚠️ {len(ignorados)} já existiam e foram ignorados: {', '.join(ignorados)}", "warning")
    for e in erros:
        flash(e, "danger")
    if not criados and not ignorados and not erros:
        flash("Nenhuma linha válida encontrada no arquivo.", "warning")

    return redirect(url_for("conferencia.nvrs_listar"))


@conferencia_bp.route("/nvrs/importar/modelo")
@login_required
def nvrs_importar_modelo():
    """Retorna um CSV modelo para o usuário baixar e preencher."""
    linhas = [
        "nvr_id;nome;site;ip;porta;usuario;senha;use_https;ativo",
        "nvr_altair_01;UFV Altair - NVR 01;Altair SP;10.38.10.202;80;admin;senha123;0;1",
        "nvr_altair_02;UFV Altair - NVR 02;Altair SP;10.38.10.203;80;admin;senha123;0;1",
        "nvr_sp_dome_01;Usina SP - Dome 01;São Paulo SP;192.168.1.100;8080;admin;outrasenha;0;1",
    ]
    return Response(
        "\n".join(linhas),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=modelo_nvrs.csv"},
    )


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
