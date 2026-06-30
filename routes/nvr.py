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
