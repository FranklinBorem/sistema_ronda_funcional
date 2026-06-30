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
