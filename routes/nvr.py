"""
routes/nvr.py — Cadastro e gerenciamento único de NVRs / câmeras.

Fonte de dados única para todo o sistema: PTZ, Conferência, polling ISAPI,
relatórios, WhatsApp e qualquer outra parte do app que precise de dados de
equipamentos deve consultar via NvrRepository / models.nvr.Nvr — nunca ter
seu próprio cadastro paralelo.
"""

from __future__ import annotations

from flask import (
    Blueprint, Response, flash, redirect, render_template,
    request, url_for, jsonify,
)

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


def _parse_conexao(form) -> dict:
    """Extrai os campos de conexão HTTP/ISAPI do formulário."""
    return {
        "porta":     int(form.get("porta", 80)),
        "use_https": "use_https" in form,
    }


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
        conexao = _parse_conexao(request.form)

        if not all([nvr_id, nome, ip, senha]):
            flash("Preencha todos os campos obrigatórios.", "warning")
            return render_template("conferencia/nvr_form.html", nvr=None, presets=[])

        try:
            _repo.criar(
                nvr_id=nvr_id, nome=nome, ip=ip, usuario=usuario, senha=senha,
                ptz_channel=ptz, snapshot_channel=snap, tempo_espera=espera,
                timeout=timeout, ativo=ativo, presets=presets, site=site,
                **conexao,
            )
            flash(f"NVR '{nome}' cadastrado com sucesso.", "success")
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
        flash("NVR não encontrado.", "danger")
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
        conexao = _parse_conexao(request.form)

        try:
            _repo.atualizar(
                nvr_id=nvr_id, nome=nome, ip=ip, usuario=usuario, senha=senha,
                ptz_channel=ptz, snapshot_channel=snap, tempo_espera=espera,
                timeout=timeout, ativo=ativo, presets=presets, site=site,
                **conexao,
            )
            flash(f"NVR '{nome}' atualizado.", "success")
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
    flash("NVR removido.", "info")
    return redirect(url_for("nvr.nvr_listar"))


# ── Importação em lote via CSV ──────────────────────────────────────────────

@nvr_bp.route("/nvrs/importar", methods=["GET", "POST"])
@login_required
def nvr_importar():
    if request.method == "GET":
        return render_template("conferencia/nvrs_importar.html")

    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename:
        flash("Nenhum arquivo enviado.", "warning")
        return redirect(url_for("nvr.nvr_importar"))

    try:
        texto = arquivo.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            arquivo.seek(0)
            texto = arquivo.read().decode("latin-1")
        except Exception:
            flash("Não foi possível decodificar o arquivo. Use UTF-8 ou Latin-1.", "danger")
            return redirect(url_for("nvr.nvr_importar"))

    criados, ignorados, erros = _repo.importar_csv(texto)

    if criados:
        flash(f"✅ {len(criados)} NVR(s) cadastrados: {', '.join(criados)}", "success")
    if ignorados:
        flash(f"⚠️ {len(ignorados)} já existiam e foram ignorados: {', '.join(ignorados)}", "warning")
    for e in erros:
        flash(e, "danger")
    if not criados and not ignorados and not erros:
        flash("Nenhuma linha válida encontrada no arquivo.", "warning")

    return redirect(url_for("nvr.nvr_listar"))


@nvr_bp.route("/nvrs/importar/modelo")
@login_required
def nvr_importar_modelo():
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
