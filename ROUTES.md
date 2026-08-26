"""
routes/__init__.py — Registro central de blueprints.
"""

from __future__ import annotations
from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .auth import auth_bp
    from .alarmes import alarmes_bp
    from .conferencia_bp import conferencia_bp
    from .dashboard import dashboard_bp
    from .email import email_bp
    from .nvr import nvr_bp
    from .ronda_loop import ronda_loop_bp
    from .rondas import rondas_bp
    from .whatsapp import whatsapp_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(rondas_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(alarmes_bp)
    app.register_blueprint(ronda_loop_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(nvr_bp)
    app.register_blueprint(conferencia_bp)

    """
routes/alarmes.py — Central de Alarmes.

Substitui alarmes_routes.py.
Sem sqlite3, sem _build_filtros() inline, sem get_db() —
toda persistência delegada ao AlertaRepository via AlarmeService
(ou diretamente ao repository, pois não há lógica de negócio adicional aqui).
"""

from __future__ import annotations

from flask import (
    Blueprint, jsonify, render_template,
    request, session,
)

from core.auth import login_required
from models.alerta import StatusAlerta
from repositories import AlertaRepository

alarmes_bp = Blueprint("alarmes", __name__)


def _repo() -> AlertaRepository:
    """Instância por request — seguro pois db.session é thread-local."""
    return AlertaRepository()


# ── Página principal ──────────────────────────────────────────────────────

@alarmes_bp.route("/alarmes")
@login_required
def central_alarmes():
    repo    = _repo()
    resumo  = repo.resumo()
    return render_template(
        "alarmes.html",
        ufvs=repo.listar_ufvs(),
        nvrs=repo.listar_nvrs(),
        total=resumo["total"],
        pendentes=resumo["pendentes"],
        deteccoes_falsas=resumo["deteccoes_falsas"],
        tratados=resumo["tratados"],
    )


# ── API — listagem paginada ────────────────────────────────────────────────

@alarmes_bp.route("/api/alarmes")
@login_required
def api_listar_alertas():
    args = request.args
    alertas, total = _repo().listar(
        status=args.get("status"),
        ufv=args.get("ufv"),
        nvr_id=args.get("nvr"),
        data_inicio=args.get("data_inicio"),
        data_fim=args.get("data_fim"),
        page=int(args.get("page", 1)),
        per_page=int(args.get("per_page", 20)),
    )
    per_page = int(args.get("per_page", 20))
    return jsonify({
        "total":    total,
        "page":     int(args.get("page", 1)),
        "per_page": per_page,
        "pages":    (total + per_page - 1) // per_page,
        "alertas":  [a.to_dict() for a in alertas],
    })


# ── API — detalhe ─────────────────────────────────────────────────────────

@alarmes_bp.route("/api/alarmes/<int:alerta_id>")
@login_required
def api_detalhe_alerta(alerta_id: int):
    alerta = _repo().buscar_por_id(alerta_id)
    if not alerta:
        return jsonify({"erro": "Alerta não encontrado"}), 404
    return jsonify(alerta.to_dict())


# ── API — tratar ──────────────────────────────────────────────────────────

@alarmes_bp.route("/api/alarmes/<int:alerta_id>/tratar", methods=["POST"])
@login_required
def api_tratar_alerta(alerta_id: int):
    data       = request.get_json(force=True) or {}
    tratativa  = (data.get("tratativa") or "").strip()
    status_raw = (data.get("status") or "pendente").strip().lower()

    # Normaliza status recebido para o enum
    if "falsa" in status_raw:
        novo_status = StatusAlerta.DETECCAO_FALSA
    elif "tratado" in status_raw:
        novo_status = StatusAlerta.TRATADO
    elif "pendente" in status_raw:
        novo_status = StatusAlerta.PENDENTE
    else:
        return jsonify({"erro": "Status inválido"}), 400

    responsavel = session.get("monitor_nome", "Desconhecido")
    repo        = _repo()
    alerta      = repo.tratar(alerta_id, novo_status, tratativa, responsavel)

    if not alerta:
        return jsonify({"erro": "Alerta não encontrado"}), 404

    from extensions import db
    db.session.commit()

    return jsonify({"ok": True, "status": alerta.status})


# ── API — reabrir ─────────────────────────────────────────────────────────

@alarmes_bp.route("/api/alarmes/<int:alerta_id>/reabrir", methods=["POST"])
@login_required
def api_reabrir_alerta(alerta_id: int):
    alerta = _repo().reabrir(alerta_id)
    if not alerta:
        return jsonify({"erro": "Alerta não encontrado"}), 404

    from extensions import db
    db.session.commit()

    return jsonify({"ok": True})


# ── API — resumo (polling dos cards) ─────────────────────────────────────

@alarmes_bp.route("/api/alarmes/resumo")
@login_required
def api_resumo():
    resumo = _repo().resumo()
    # Mantém chave "tratando" para compatibilidade com o JS existente
    resumo["tratando"] = resumo["deteccoes_falsas"]
    return jsonify(resumo)

"""
routes/auth.py — Autenticação de monitores.

Substitui auth_routes.py.
Toda lógica de verificação de senha delegada ao MonitorRepository
via o método verificar_senha() do model Monitor.
Sem sqlite3, sem check_password_hash inline, sem get_db().
"""

from __future__ import annotations

from flask import (
    Blueprint, flash, redirect,
    render_template, request, session, url_for,
)

from core.auth import login_required
from repositories import MonitorRepository

auth_bp = Blueprint("auth", __name__)

_repo = MonitorRepository()


@auth_bp.route("/")
def index():
    if "monitor_id" in session:
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha   = request.form.get("senha", "")

        monitor = _repo.buscar_por_usuario(usuario)

        if monitor and monitor.verificar_senha(senha):
            session.clear()
            session["monitor_id"]    = monitor.id
            session["monitor_nome"]  = monitor.nome
            session["monitor_turno"] = monitor.turno
            flash(f"Bem-vindo, {monitor.nome}!", "success")
            return redirect(url_for("dashboard.dashboard"))

        flash("Usuário ou senha incorretos.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    response = redirect(url_for("auth.login"))
    response.set_cookie("session", "", expires=0)
    flash("Sessão encerrada.", "info")
    return response

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

"""
routes/dashboard.py — Dashboard principal.

Substitui dashboard_routes.py.
A rota apenas lê o parâmetro `dias` e delega tudo ao DashboardService.
"""

from __future__ import annotations

from flask import Blueprint, render_template, request

from core.auth import login_required
from services import DashboardService

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    dias = int(request.args.get("dias", 30))
    context = DashboardService(dias=dias).build_context()
    return render_template("dashboard.html", **context)

"""
routes/email.py — Envio de relatórios de ronda por e-mail.

Substitui email_routes.py.
Sem sqlite3, sem smtplib inline, sem _gerar_html_relatorio() —
tudo delegado ao EmailService.
"""

from __future__ import annotations

from flask import (
    Blueprint, jsonify, render_template, request,
)

from core.auth import login_required
from services import EmailService, EnvioEmail, FiltroEmail

email_bp = Blueprint("email", __name__)


# ── Página de configuração/listagem ──────────────────────────────────────

@email_bp.route("/email")
@login_required
def email_config():
    filtro  = FiltroEmail()
    context = EmailService().montar_contexto_listagem(filtro)
    return render_template("email_config.html", **context)


# ── API — listagem de rondas filtrada ─────────────────────────────────────

@email_bp.route("/api/email/rondas")
@login_required
def api_email_rondas():
    filtro = FiltroEmail(
        data_ini=request.args.get("data_ini") or None,
        data_fim=request.args.get("data_fim") or None,
        turno=request.args.get("turno") or None,
        monitor_nome=request.args.get("monitor") or None,
        status=request.args.get("status") or None,
    )
    context = EmailService().montar_contexto_listagem(filtro)
    rondas  = [
        {
            "id":            r.id,
            "monitor_nome":  r.monitor_nome,
            "turno":         r.turno,
            "iniciada_em":   r.iniciada_em.isoformat() if r.iniciada_em else None,
            "finalizada_em": r.finalizada_em.isoformat() if r.finalizada_em else None,
            "status":        r.status,
        }
        for r in context["rondas"]
    ]
    return jsonify({"rondas": rondas})


# ── API — preview do e-mail ───────────────────────────────────────────────

@email_bp.route("/api/email/preview/<int:ronda_id>")
@login_required
def api_email_preview(ronda_id: int):
    from repositories import RondaRepository
    ronda = RondaRepository().buscar_por_id(ronda_id)
    if not ronda:
        return "<p style='color:red;padding:20px'>Ronda não encontrada.</p>", 404

    # Reutiliza o renderizador interno do EmailService
    service = EmailService()
    html = service._renderizar_template([ronda], f"Preview — Ronda #{ronda_id}")
    return html


# ── API — envio ───────────────────────────────────────────────────────────

@email_bp.route("/api/email/enviar-relatorio", methods=["POST"])
@login_required
def api_enviar_relatorio():
    data = request.get_json(force=True) or {}

    ronda_ids     = data.get("ronda_ids") or []
    # Suporte ao formato legado que envia ronda_id (singular)
    if not ronda_ids and data.get("ronda_id"):
        ronda_ids = [data["ronda_id"]]

    destinatario = (data.get("destinatario") or "").strip()
    if not destinatario:
        # Suporte ao formato legado que envia lista "destinatarios"
        destinatarios = data.get("destinatarios", [])
        destinatario  = destinatarios[0] if destinatarios else ""

    if not ronda_ids:
        return jsonify({"ok": False, "erro": "Nenhuma ronda selecionada"}), 400
    if not destinatario:
        return jsonify({"ok": False, "erro": "Nenhum destinatário informado"}), 400

    envio = EnvioEmail(
        destinatario=destinatario,
        ronda_ids=[int(rid) for rid in ronda_ids],
        assunto=data.get("assunto", "Relatório de Ronda — Grupo Ronda"),
        incluir_imagens=data.get("incluir_imagens", True),
    )

    sucesso, mensagem = EmailService().enviar_relatorio(envio)
    if sucesso:
        return jsonify({"ok": True, "mensagem": mensagem})
    return jsonify({"ok": False, "erro": mensagem}), 500

"""
routes/nvr.py — Cadastro e gerenciamento de câmeras PTZ.

Substitui nvr_routes.py (SQLite puro).
Usa NvrRepository + SQLAlchemy. Sem sqlite3, sem get_db(), sem nvr_db.
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify

from core.auth import login_required
from repositories.nvr_repository import NvrRepository

nvr_bp = Blueprint("nvr", __name__)

_repo = NvrRepository()


def _parse_presets(form) -> dict[int, str]:
    """Extrai presets do formulário → {numero: nome}."""
    nums  = form.getlist("preset_num[]")
    nomes = form.getlist("preset_nome[]")
    result = {}
    for n, nm in zip(nums, nomes):
        n_str  = str(n).strip()
        nm_str = str(nm).strip()
        if n_str and nm_str:
            try:
                result[int(n_str)] = nm_str
            except ValueError:
                pass
    return result


# ── Listagem ───────────────────────────────────────────────────────────────

@nvr_bp.route("/nvrs")
@login_required
def nvr_listar():
    nvrs = _repo.listar()
    return render_template("conferencia/nvrs.html", nvrs=nvrs, migrados=0)


# ── Novo cadastro ──────────────────────────────────────────────────────────

@nvr_bp.route("/nvrs/novo", methods=["GET", "POST"])
@login_required
def nvr_novo():
    if request.method == "POST":
        nvr_id  = request.form.get("nvr_id", "").strip().replace(" ", "_")
        nome    = request.form.get("nome", "").strip()
        ip      = request.form.get("ip", "").strip()
        usuario = request.form.get("usuario", "admin").strip()
        senha   = request.form.get("senha", "").strip()
        site    = request.form.get("site", "").strip()
        ptz     = int(request.form.get("ptz_channel", 1))
        snap    = request.form.get("snapshot_channel", "501").strip()
        espera  = int(request.form.get("tempo_espera", 5))
        timeout = int(request.form.get("timeout", 10))
        ativo   = bool(request.form.get("ativo"))
        presets = _parse_presets(request.form)

        if not all([nvr_id, nome, ip, senha]):
            flash("Preencha todos os campos obrigatórios.", "warning")
            return render_template("conferencia/nvr_form.html", nvr=None, presets=[])

        try:
            _repo.criar(
                nvr_id=nvr_id, nome=nome, ip=ip, usuario=usuario, senha=senha,
                ptz_channel=ptz, snapshot_channel=snap, tempo_espera=espera,
                timeout=timeout, ativo=ativo, presets=presets, site=site,
            )
            flash(f"PTZ '{nome}' cadastrada com sucesso.", "success")
            return redirect(url_for("nvr.nvr_listar"))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Erro inesperado: {e}", "danger")

    return render_template("conferencia/nvr_form.html", nvr=None, presets=[])


# ── Edição ─────────────────────────────────────────────────────────────────

@nvr_bp.route("/nvrs/<nvr_id>/editar", methods=["GET", "POST"])
@login_required
def nvr_editar(nvr_id: str):
    nvr = _repo.buscar_por_nvr_id(nvr_id)
    if not nvr:
        flash("PTZ não encontrada.", "danger")
        return redirect(url_for("nvr.nvr_listar"))

    if request.method == "POST":
        nome    = request.form.get("nome", "").strip()
        ip      = request.form.get("ip", "").strip()
        usuario = request.form.get("usuario", "admin").strip()
        senha   = request.form.get("senha", "").strip() or None  # None = manter atual
        site    = request.form.get("site", "").strip()
        ptz     = int(request.form.get("ptz_channel", 1))
        snap    = request.form.get("snapshot_channel", "501").strip()
        espera  = int(request.form.get("tempo_espera", 5))
        timeout = int(request.form.get("timeout", 10))
        ativo   = bool(request.form.get("ativo"))
        presets = _parse_presets(request.form)

        try:
            _repo.atualizar(
                nvr_id=nvr_id, nome=nome, ip=ip, usuario=usuario, senha=senha,
                ptz_channel=ptz, snapshot_channel=snap, tempo_espera=espera,
                timeout=timeout, ativo=ativo, presets=presets, site=site,
            )
            flash(f"PTZ '{nome}' atualizada.", "success")
            return redirect(url_for("nvr.nvr_listar"))
        except Exception as e:
            flash(f"Erro: {e}", "danger")

    return render_template("conferencia/nvr_form.html", nvr=nvr, presets=nvr.presets)


# ── Toggle ativo ───────────────────────────────────────────────────────────

@nvr_bp.route("/nvrs/<nvr_id>/toggle", methods=["POST"])
@login_required
def nvr_toggle(nvr_id: str):
    try:
        _repo.toggle_ativo(nvr_id)
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("nvr.nvr_listar"))


# ── Exclusão ───────────────────────────────────────────────────────────────

@nvr_bp.route("/nvrs/<nvr_id>/excluir", methods=["POST"])
@login_required
def nvr_excluir(nvr_id: str):
    _repo.excluir(nvr_id)
    flash("PTZ removida.", "info")
    return redirect(url_for("nvr.nvr_listar"))


# ── API ────────────────────────────────────────────────────────────────────

@nvr_bp.route("/api/nvrs/ativos")
@login_required
def api_nvrs_ativos():
    nvrs = _repo.listar(apenas_ativos=True)
    return jsonify({
        "nvrs": [
            {"id": n.id, "nvr_id": n.nvr_id, "nome": n.nome, "ip": n.ip, "site": n.site or ""}
            for n in nvrs
        ]
    })

"""
routes/ronda_loop.py — Controle do loop de ronda contínua.

Substitui ronda_loop_routes.py.
As funções do motor (iniciar_loop, parar_loop, status_loop) continuam
sendo importadas diretamente de core.ronda_loop — o loop é estado
global de processo e não precisa de um service intermediário.
"""

from __future__ import annotations

from flask import (
    Blueprint, jsonify, render_template,
    request, session,
)

from core.auth import login_required
from core.ronda_loop import iniciar_loop, parar_loop, status_loop
from repositories.nvr_repository import NvrRepository

ronda_loop_bp = Blueprint("ronda_loop", __name__)

_nvr_repo = NvrRepository()


# ── Página de controle ────────────────────────────────────────────────────

@ronda_loop_bp.route("/ronda-loop")
@login_required
def pagina_loop():
    nvrs_disponiveis = [
        {"id": n.nvr_id, "nome": n.nome, "site": n.site or "", "ip": n.ip}
        for n in _nvr_repo.listar(apenas_ativos=True)
    ]
    return render_template(
        "ronda_loop.html",
        nvrs=nvrs_disponiveis,
        monitor_nome=session.get("monitor_nome", ""),
        turno=session.get("monitor_turno", ""),
    )


# ── API — iniciar ─────────────────────────────────────────────────────────

@ronda_loop_bp.route("/api/ronda-loop/iniciar", methods=["POST"])
@login_required
def api_iniciar():
    data = request.get_json(force=True) or {}

    resultado = iniciar_loop(
        monitor_id=session.get("monitor_id"),
        monitor_nome=data.get("monitor_nome") or session.get("monitor_nome", "Não informado"),
        turno=data.get("turno") or session.get("monitor_turno", "Não informado"),
        nvr_ids=data.get("nvr_ids") or None,
    )
    return jsonify(resultado)


# ── API — parar ───────────────────────────────────────────────────────────

@ronda_loop_bp.route("/api/ronda-loop/parar", methods=["POST"])
@login_required
def api_parar():
    return jsonify(parar_loop())


# ── API — status ──────────────────────────────────────────────────────────

@ronda_loop_bp.route("/api/ronda-loop/status")
@login_required
def api_status():
    return jsonify(status_loop())

"""
routes/ronda_loop.py — Controle do loop de ronda contínua.

Substitui ronda_loop_routes.py.

As funções do motor (iniciar_loop, parar_loop, status_loop) continuam
sendo importadas diretamente de core.ronda_loop — o loop é estado
global de processo e não precisa de um service intermediário.
"""
from __future__ import annotations

from flask import (
    Blueprint, jsonify, render_template,
    request, session,
)

from core.auth import login_required
from core.nvr_config import carregar_nvrs
from core.ronda_loop import iniciar_loop, parar_loop, status_loop

ronda_loop_bp = Blueprint("ronda_loop", __name__)


# ── Página de controle ──────────────────────────────────────────────────

@ronda_loop_bp.route("/ronda-loop")
@login_required
def pagina_loop():
    nvrs_disponiveis = [
        {"id": n.id, "nome": n.nome, "site": n.site, "ip": n.ip}
        for n in carregar_nvrs()
    ]
    return render_template(
        "ronda_loop.html",
        nvrs=nvrs_disponiveis,
        monitor_nome=session.get("monitor_nome", ""),
        turno=session.get("monitor_turno", ""),
    )


# ── API — iniciar ───────────────────────────────────────────────────────

@ronda_loop_bp.route("/api/ronda-loop/iniciar", methods=["POST"])
@login_required
def api_iniciar():
    data = request.get_json(force=True) or {}
    resultado = iniciar_loop(
        monitor_id=session.get("monitor_id"),
        monitor_nome=data.get("monitor_nome") or session.get("monitor_nome", "Não informado"),
        turno=data.get("turno") or session.get("monitor_turno", "Não informado"),
        nvr_ids=data.get("nvr_ids") or None,
    )
    return jsonify(resultado)


# ── API — parar ──────────────────────────────────────────────────────────

@ronda_loop_bp.route("/api/ronda-loop/parar", methods=["POST"])
@login_required
def api_parar():
    return jsonify(parar_loop())


# ── API — status ─────────────────────────────────────────────────────────

@ronda_loop_bp.route("/api/ronda-loop/status")
@login_required
def api_status():
    return jsonify(status_loop())

"""
routes/rondas.py — Rondas, histórico, monitores e relatórios.

Substitui rondas_routes.py.
Sem sqlite3, sem get_db(), sem IntegrityError inline —
tudo delegado ao RondaService.
"""

from __future__ import annotations

from flask import (
    Blueprint, flash, jsonify, redirect,
    render_template, request, send_from_directory,
    session, url_for,
)

from core.auth import login_required
from config import BaseConfig
from services import RondaService

rondas_bp = Blueprint("rondas", __name__)


# ── Arquivos estáticos de relatórios ──────────────────────────────────────

@rondas_bp.route("/relatorios/<path:filename>")
@rondas_bp.route("/relatorios_img/<path:filename>")
def servir_arquivo_relatorio(filename: str):
    return send_from_directory(BaseConfig.RELATORIOS_DIR.resolve(), filename)


# ── Ronda simples ─────────────────────────────────────────────────────────

@rondas_bp.route("/iniciar_ronda", methods=["POST"])
@login_required
def iniciar_ronda():
    RondaService().iniciar_ronda(
        monitor_id=session["monitor_id"],
        monitor_nome=session["monitor_nome"],
        turno=session["monitor_turno"],
    )
    flash("Ronda iniciada! Acompanhe o progresso abaixo.", "success")
    return redirect(url_for("dashboard.dashboard"))


# ── Ronda multi-NVR ───────────────────────────────────────────────────────

@rondas_bp.route("/iniciar_ronda_multi", methods=["POST"])
@login_required
def iniciar_ronda_multi():
    nvr_ids = request.form.getlist("nvrs")
    service = RondaService()
    service.iniciar_ronda_multi(
        monitor_id=session["monitor_id"],
        monitor_nome=session["monitor_nome"],
        turno=session["monitor_turno"],
        nvr_ids=nvr_ids or None,
    )
    flash(
        f"Ronda multi-NVR iniciada em {service.quantidade_nvrs(nvr_ids)} NVR(s)!",
        "success",
    )
    return redirect(url_for("rondas.historico"))


# ── Histórico ─────────────────────────────────────────────────────────────

@rondas_bp.route("/historico")
@login_required
def historico():
    rondas = RondaService().listar_historico()
    return render_template("historico.html", rondas=rondas)


# ── Relatórios ────────────────────────────────────────────────────────────

@rondas_bp.route("/relatorio/<int:ronda_id>")
@login_required
def ver_relatorio(ronda_id: int):
    # Compatibilidade com links antigos — redireciona para multi
    return redirect(url_for("rondas.ver_relatorio_multi", ronda_id=ronda_id))


@rondas_bp.route("/relatorio_multi/<int:ronda_id>")
@login_required
def ver_relatorio_multi(ronda_id: int):
    context = RondaService().montar_relatorio_multi_context(ronda_id)
    if not context:
        flash("Relatório não encontrado.", "danger")
        return redirect(url_for("rondas.historico"))
    return render_template("relatorio_multi.html", **context)


# ── Monitores ─────────────────────────────────────────────────────────────

@rondas_bp.route("/monitores")
@login_required
def monitores():
    lista = RondaService().listar_monitores()
    return render_template("monitores.html", monitores=lista)


@rondas_bp.route("/monitores/novo", methods=["GET", "POST"])
@login_required
def novo_monitor():
    if request.method == "POST":
        nome    = request.form.get("nome", "").strip()
        usuario = request.form.get("usuario", "").strip()
        senha   = request.form.get("senha", "")
        turno   = request.form.get("turno", "").strip()

        if not all([nome, usuario, senha, turno]):
            flash("Preencha todos os campos.", "warning")
            return render_template("novo_monitor.html")

        sucesso, erro = RondaService().cadastrar_monitor(nome, usuario, senha, turno)
        if sucesso:
            flash(f"Monitor '{nome}' cadastrado com sucesso.", "success")
            return redirect(url_for("rondas.monitores"))

        flash(erro, "danger")

    return render_template("novo_monitor.html")


# ── API ───────────────────────────────────────────────────────────────────

@rondas_bp.route("/api/ronda/<int:ronda_id>/status")
@login_required
def api_status_ronda(ronda_id: int):
    payload, status_code = RondaService().status_ronda(ronda_id)
    return jsonify(payload), status_code

"""
routes/whatsapp.py — Conector WhatsApp e monitor de grupos.

Substitui whatsapp_routes.py.
Sem sqlite3, sem get_db() — delegado ao WhatsAppMonitorService.
O commit da sessão é feito aqui, após cada operação de escrita,
mantendo a rota responsável pelo ciclo de transação.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from core.auth import login_required
from extensions import db
from services import WhatsAppMonitorService

whatsapp_bp = Blueprint("whatsapp", __name__)


@whatsapp_bp.route("/mensagens", methods=["POST"])
def receber_mensagem():
    payload, status_code = WhatsAppMonitorService().registrar_mensagem(
        request.json or {}
    )
    if status_code == 200 and payload.get("status") == "ok":
        db.session.commit()
    return jsonify(payload), status_code


@whatsapp_bp.route("/heartbeat", methods=["POST"])
def heartbeat():
    timestamp = (request.json or {}).get("timestamp")
    payload = WhatsAppMonitorService().registrar_heartbeat(timestamp)
    db.session.commit()
    return jsonify(payload), 200


@whatsapp_bp.route("/monitor-whatsapp")
@login_required
def monitor_whatsapp():
    context = WhatsAppMonitorService().montar_contexto_monitor()
    return render_template("monitor_whatsapp.html", **context)
