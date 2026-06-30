"""
services/email_service.py — Envio de e-mails de relatório de ronda.

Responsabilidades:
  - Montar o contexto de filtro/listagem para a rota /email
  - Renderizar o corpo HTML do e-mail a partir de um template Jinja2
  - Enviar via SMTP com anexo de imagens (multipart/related)
  - Registrar o envio no log de auditoria (opcional, extensível)

Não importa sqlite3 nem queries SQL — apenas RondaRepository e
MonitorRepository.

Configuração SMTP esperada em config.py (ou variáveis de ambiente):
    MAIL_SERVER   = "smtp.example.com"
    MAIL_PORT     = 587
    MAIL_USE_TLS  = True
    MAIL_USERNAME = "vigilante@example.com"
    MAIL_PASSWORD = "secret"
    MAIL_SENDER   = "Vigilante IA <vigilante@example.com>"
    MAIL_DEFAULT_RECEIVER = "seguranca@example.com"
"""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from flask import current_app, render_template

from repositories.monitor_repository import MonitorRepository
from repositories.ronda_repository import RondaRepository


# ── Tipos de dados ─────────────────────────────────────────────────────────

@dataclass
class FiltroEmail:
    """Parâmetros de filtro vindos do formulário da rota /email."""
    data_ini: str | None = None
    data_fim: str | None = None
    turno: str | None = None
    monitor_nome: str | None = None
    status: str | None = None


@dataclass
class EnvioEmail:
    """Parâmetros do envio vindo do formulário da rota /email/enviar."""
    destinatario: str
    ronda_ids: list[int] = field(default_factory=list)
    assunto: str = "Relatório de Ronda — Vigilante IA"
    incluir_imagens: bool = True


# ── Service ────────────────────────────────────────────────────────────────

class EmailService:
    """Monta e envia e-mails de relatório de ronda."""

    def __init__(
        self,
        ronda_repo: RondaRepository | None = None,
        monitor_repo: MonitorRepository | None = None,
    ) -> None:
        self._ronda_repo = ronda_repo or RondaRepository()
        self._monitor_repo = monitor_repo or MonitorRepository()

    # ── Contexto para a rota /email ────────────────────────────────────────

    def montar_contexto_listagem(self, filtro: FiltroEmail) -> dict[str, Any]:
        """
        Retorna o dicionário de contexto para o template email_listagem.html.
        Inclui as rondas filtradas e as opções dos selects de filtro.
        """
        rondas = self._ronda_repo.listar_filtrado(
            data_ini=filtro.data_ini,
            data_fim=filtro.data_fim,
            turno=filtro.turno,
            monitor_nome=filtro.monitor_nome,
            status=filtro.status,
        )
        monitores = self._monitor_repo.listar_nomes()

        return {
            "rondas": rondas,
            "monitores": monitores,
            "filtro": filtro,
            "turnos": ["diurno", "noturno", "madrugada"],
            "status_opcoes": ["em_andamento", "finalizada", "com_alertas", "erro"],
        }

    # ── Envio ──────────────────────────────────────────────────────────────

    def enviar_relatorio(self, envio: EnvioEmail) -> tuple[bool, str]:
        """
        Compila o e-mail com as rondas selecionadas e envia via SMTP.
        Retorna (sucesso, mensagem).

        Fluxo:
          1. Busca os objetos Ronda pelos IDs selecionados
          2. Renderiza o template HTML do e-mail
          3. Monta a mensagem MIME (texto + imagens inline opcionais)
          4. Envia via SMTP com TLS
        """
        rondas = [
            self._ronda_repo.buscar_por_id(rid)
            for rid in envio.ronda_ids
        ]
        rondas = [r for r in rondas if r is not None]

        if not rondas:
            return False, "Nenhuma ronda válida selecionada."

        html_body = self._renderizar_template(rondas, envio.assunto)
        mensagem = self._montar_mime(envio, html_body, rondas)

        try:
            self._enviar_smtp(envio.destinatario, mensagem)
            return True, f"E-mail enviado para {envio.destinatario}."
        except smtplib.SMTPAuthenticationError:
            return False, "Falha de autenticação SMTP. Verifique usuário e senha."
        except smtplib.SMTPConnectError:
            return False, "Não foi possível conectar ao servidor SMTP."
        except Exception as exc:
            return False, f"Erro ao enviar e-mail: {exc}"

    # ── Internos ───────────────────────────────────────────────────────────

    def _renderizar_template(self, rondas: list, assunto: str) -> str:
        """
        Renderiza o template Jinja2 do corpo do e-mail.
        O template espera: rondas, assunto, gerado_em.

        Se o template não existir (ambiente de teste, por exemplo),
        gera um HTML mínimo como fallback.
        """
        try:
            return render_template(
                "email/relatorio_ronda.html",
                rondas=rondas,
                assunto=assunto,
                gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"),
            )
        except Exception:
            # Fallback para ambientes sem o template
            linhas = [
                f"<h2>{assunto}</h2>",
                f"<p>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>",
                "<ul>",
                *[
                    f"<li>Ronda #{r.id} — {r.monitor_nome} — {r.turno} — {r.status}</li>"
                    for r in rondas
                ],
                "</ul>",
            ]
            return "\n".join(linhas)

    def _montar_mime(
        self,
        envio: EnvioEmail,
        html_body: str,
        rondas: list,
    ) -> MIMEMultipart:
        """
        Constrói a mensagem MIME multipart/related.
        Imagens inline são referenciadas no HTML como cid:<nome_arquivo>.
        """
        cfg = current_app.config
        remetente = cfg.get("MAIL_SENDER", cfg.get("MAIL_USERNAME", ""))

        msg = MIMEMultipart("related")
        msg["Subject"] = envio.assunto
        msg["From"] = remetente
        msg["To"] = envio.destinatario

        # Parte alternativa: texto puro + HTML
        alternativo = MIMEMultipart("alternative")
        texto_puro = self._html_para_texto(html_body)
        alternativo.attach(MIMEText(texto_puro, "plain", "utf-8"))
        alternativo.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alternativo)

        if envio.incluir_imagens:
            self._anexar_imagens(msg, rondas)

        return msg

    @staticmethod
    def _anexar_imagens(msg: MIMEMultipart, rondas: list) -> None:
        """
        Anexa as imagens de alerta de cada ronda como partes inline.
        Usa o campo imagem_path dos alertas associados.
        Silencia erros de arquivo não encontrado para não interromper o envio.
        """
        for ronda in rondas:
            if not hasattr(ronda, "alertas"):
                continue
            for alerta in ronda.alertas:
                if not alerta.imagem_path:
                    continue
                caminho = Path(alerta.imagem_path)
                if not caminho.exists():
                    continue
                try:
                    with caminho.open("rb") as f:
                        img = MIMEImage(f.read())
                    img.add_header("Content-ID", f"<{caminho.name}>")
                    img.add_header(
                        "Content-Disposition", "inline", filename=caminho.name
                    )
                    msg.attach(img)
                except Exception:
                    continue

    def _enviar_smtp(self, destinatario: str, mensagem: MIMEMultipart) -> None:
        """
        Realiza a conexão SMTP e envia a mensagem.
        Suporta TLS (STARTTLS na porta 587) e SSL direto (porta 465).
        """
        cfg = current_app.config
        server = cfg.get("MAIL_SERVER", "localhost")
        port = int(cfg.get("MAIL_PORT", 587))
        use_tls = cfg.get("MAIL_USE_TLS", True)
        use_ssl = cfg.get("MAIL_USE_SSL", False)
        username = cfg.get("MAIL_USERNAME")
        password = cfg.get("MAIL_PASSWORD")
        remetente = cfg.get("MAIL_SENDER", username or "")

        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, context=context) as smtp:
                if username and password:
                    smtp.login(username, password)
                smtp.sendmail(remetente, destinatario, mensagem.as_string())
        else:
            with smtplib.SMTP(server, port) as smtp:
                if use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                if username and password:
                    smtp.login(username, password)
                smtp.sendmail(remetente, destinatario, mensagem.as_string())

    @staticmethod
    def _html_para_texto(html: str) -> str:
        """
        Remove tags HTML para gerar uma versão texto puro do e-mail.
        Solução simples sem dependências externas.
        """
        import re
        sem_tags = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s{2,}", "\n", sem_tags).strip()
