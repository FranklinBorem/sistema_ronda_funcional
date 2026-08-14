"""
routes/equipamentos.py — Cadastro de NVR (grupo/site) e Câmera
(via_nvr ou ip_direto) no schema novo (Fase B da religação).

Substitui, quando religado em routes/__init__.py, routes/nvr.py e a
parte de CRUD de NVR de routes/conferencia_bp.py (que gerenciava o
antigo NvrMonitorado). O restante de routes/conferencia_bp.py
(polling/dashboard de disponibilidade) é Fase D — fora do escopo
deste arquivo.

IMPORTANTE: este blueprint ainda NÃO está registrado em
routes/__init__.py (ver decisão em docs/decisions/decisoes-pendentes.md
sobre religação atômica) — fica pronto e testado isoladamente até a
etapa final de corte, quando todos os blueprints forem trocados juntos.
"""

from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from core.auth import login_required
from repositories_v2.nvr_repository import NvrRepository

equipamentos_bp = Blueprint("equipamentos", __name__)

_repo = NvrRepository()

# TODO(Fase 2 - multi-tenant/UI de unidades): hoje só existe uma
# Unidade operando; o formulário não pede unidade porque não há
# seletor de unidade na UI ainda. Quando isso mudar, resolver a partir
# de session["empresa_id"] + um campo de unidade no formulário, em vez
# de assumir a primeira unidade cadastrada.
def _unidade_padrao_id() -> int | None:
    from models_v2.unidade import Unidade
    from extensions import db
    primeira = db.session.query(Unidade).order_by(Unidade.id).first()
    return primeira.id if primeira else None


# ── Listagem ─────────────────────────────────────────────────────────────

@equipamentos_bp.route("/equipamentos")
@login_required
def listar():
    unidade_id = _unidade_padrao_id()
    nvrs = _repo.listar_por_unidade(unidade_id) if unidade_id else []
    nvrs_com_cameras = [
        {"nvr": nvr, "cameras": _repo.listar_cameras(nvr.id)} for nvr in nvrs
    ]
    return render_template("equipamentos/listar.html", nvrs_com_cameras=nvrs_com_cameras)


# ── Cadastro de NVR (com opção de subir o NVR inteiro ou só o grupo) ──────

@equipamentos_bp.route("/equipamentos/nvr/novo", methods=["GET", "POST"])
@login_required
def nvr_novo():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        endereco_ip = request.form.get("endereco_ip", "").strip() or None
        usuario_acesso = request.form.get("usuario_acesso", "").strip() or None
        senha = request.form.get("senha", "").strip() or None
        porta = int(request.form.get("porta") or 80)
        unidade_id = _unidade_padrao_id()

        if not nome or not unidade_id:
            flash("Preencha o nome do NVR/grupo e cadastre uma Unidade antes.", "warning")
            return render_template("equipamentos/nvr_form.html")

        if endereco_ip and usuario_acesso and senha:
            # "Subir o NVR" — tenta descobrir os canais automaticamente
            nvr, cameras, erro = _repo.cadastrar_nvr_com_descoberta(
                unidade_id=unidade_id, nome=nome, endereco_ip=endereco_ip,
                usuario_acesso=usuario_acesso, senha_plain=senha, porta=porta,
            )
            from extensions import db
            db.session.commit()
            if erro:
                flash(
                    f"NVR '{nome}' cadastrado, mas não foi possível consultar os canais "
                    f"automaticamente ({erro}). Cadastre as câmeras manualmente.",
                    "warning",
                )
            else:
                flash(f"NVR '{nome}' cadastrado com {len(cameras)} câmera(s) descoberta(s).", "success")
        else:
            # "Só o grupo/site" — sem dispositivo físico, câmeras avulsas depois
            nvr = _repo.criar_nvr(unidade_id=unidade_id, nome=nome)
            from extensions import db
            db.session.commit()
            flash(f"Grupo '{nome}' criado. Cadastre as câmeras avulsas dentro dele.", "success")

        return redirect(url_for("equipamentos.listar"))

    return render_template("equipamentos/nvr_form.html")


@equipamentos_bp.route("/equipamentos/nvr/<int:nvr_id>/excluir", methods=["POST"])
@login_required
def nvr_excluir(nvr_id: int):
    nvr = _repo.buscar_por_id(nvr_id)
    if nvr:
        from extensions import db
        _repo.excluir_nvr(nvr)
        db.session.commit()
        flash("NVR/grupo removido.", "info")
    return redirect(url_for("equipamentos.listar"))


# ── Cadastro de câmera avulsa (ip_direto), sempre dentro de um NVR/grupo ──

@equipamentos_bp.route("/equipamentos/nvr/<int:nvr_id>/camera/nova", methods=["GET", "POST"])
@login_required
def camera_nova(nvr_id: int):
    nvr = _repo.buscar_por_id(nvr_id)
    if not nvr:
        flash("NVR/grupo não encontrado.", "danger")
        return redirect(url_for("equipamentos.listar"))

    if request.method == "POST":
        tipo = request.form.get("tipo", "generica")
        nome = request.form.get("nome", "").strip() or None
        endereco_ip = request.form.get("endereco_ip", "").strip()
        usuario_acesso = request.form.get("usuario_acesso", "").strip() or None
        senha = request.form.get("senha", "").strip() or None
        porta = int(request.form.get("porta") or 80)

        if not endereco_ip:
            flash("Informe o endereço IP da câmera avulsa.", "warning")
            return render_template("equipamentos/camera_form.html", nvr=nvr)

        from extensions import db
        _repo.criar_camera(
            nvr_id=nvr.id, modo_conexao="ip_direto", tipo=tipo,
            endereco_ip=endereco_ip, porta=porta,
            usuario_acesso=usuario_acesso, credencial_ref=senha, nome=nome,
        )
        db.session.commit()
        flash("Câmera avulsa cadastrada.", "success")
        return redirect(url_for("equipamentos.listar"))

    return render_template("equipamentos/camera_form.html", nvr=nvr)


@equipamentos_bp.route("/equipamentos/camera/<int:camera_id>/excluir", methods=["POST"])
@login_required
def camera_excluir(camera_id: int):
    camera = _repo.buscar_camera(camera_id)
    if camera:
        from extensions import db
        _repo.excluir_camera(camera)
        db.session.commit()
        flash("Câmera removida.", "info")
    return redirect(url_for("equipamentos.listar"))


# ── API ──────────────────────────────────────────────────────────────────

@equipamentos_bp.route("/api/equipamentos/nvrs")
@login_required
def api_nvrs():
    unidade_id = _unidade_padrao_id()
    nvrs = _repo.listar_por_unidade(unidade_id) if unidade_id else []
    return jsonify({
        "nvrs": [
            {**n.to_dict(), "cameras": [c.to_dict() for c in _repo.listar_cameras(n.id)]}
            for n in nvrs
        ]
    })
