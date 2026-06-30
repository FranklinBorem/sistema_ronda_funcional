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
