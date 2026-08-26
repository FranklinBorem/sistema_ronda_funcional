"""
repositories/__init__.py

Exporta todos os repositories para import direto.
"""

from .alerta_repository import AlertaRepository
from .mensagem_repository import MensagemRepository
from .monitor_repository import MonitorRepository
from .ronda_repository import RondaRepository

__all__ = [
    "AlertaRepository",
    "MensagemRepository",
    "MonitorRepository",
    "RondaRepository",
]

"""
repositories/alerta_repository.py — Acesso a dados de alertas.

Substitui:
  - alarmes_schema.py (registrar_alerta, queries diretas sqlite3)
  - alarmes_routes.py (queries inline _build_filtros)

Este repository é o único chamado diretamente pelo motor de ronda
(ronda_multi_nvr.py) fora do Flask context — a injeção de sessão
da BaseRepository resolve isso de forma transparente.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import desc, func

from models.alerta import Alerta, StatusAlerta
from .base import BaseRepository


class AlertaRepository(BaseRepository):

    # ── Escrita ────────────────────────────────────────────────────────────

    def registrar(
        self,
        nvr_id: str,
        nvr_nome: str,
        local_preset: str,
        pessoas: int,
        detectado_em: datetime,
        ronda_id: int | None = None,
        ufv: str | None = None,
        imagem_path: str | None = None,
    ) -> Alerta:
        """
        Persiste um alerta gerado pelo YOLO.
        Substitui registrar_alerta() de alarmes_schema.py.
        Seguro para uso em threads (injetar Session explícita).
        """
        alerta = Alerta(
            ronda_id=ronda_id,
            nvr_id=nvr_id,
            nvr_nome=nvr_nome,
            ufv=ufv,
            local_preset=local_preset,
            pessoas=pessoas,
            imagem_path=imagem_path,
            detectado_em=detectado_em,
            status=StatusAlerta.PENDENTE.value,
        )
        self.session.add(alerta)
        self.session.flush()
        return alerta

    def tratar(
        self,
        alerta_id: int,
        novo_status: StatusAlerta,
        tratativa: str,
        responsavel: str,
    ) -> Optional[Alerta]:
        """Registra tratativa. Retorna None se o alerta não existir."""
        alerta = self.session.get(Alerta, alerta_id)
        if not alerta:
            return None
        alerta.tratar(novo_status, tratativa, responsavel)
        return alerta

    def reabrir(self, alerta_id: int) -> Optional[Alerta]:
        alerta = self.session.get(Alerta, alerta_id)
        if not alerta:
            return None
        alerta.reabrir()
        return alerta

    # ── Leitura — item único ───────────────────────────────────────────────

    def buscar_por_id(self, alerta_id: int) -> Optional[Alerta]:
        return self.session.get(Alerta, alerta_id)

    # ── Leitura — listagem paginada com filtros ────────────────────────────

    def listar(
        self,
        status: str | None = None,
        ufv: str | None = None,
        nvr_id: str | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Alerta], int]:
        """
        Retorna (alertas_da_página, total).
        Substitui _build_filtros() + queries de alarmes_routes.py.
        Só inclui detecções reais de pessoas (pessoas > 0).
        """
        q = (
            self.session
            .query(Alerta)
            .filter(Alerta.pessoas > 0)
        )

        if status and status != "todos":
            q = q.filter(Alerta.status == status)
        if ufv:
            q = q.filter(Alerta.ufv == ufv)
        if nvr_id:
            q = q.filter(Alerta.nvr_id == nvr_id)
        if data_inicio:
            q = q.filter(Alerta.detectado_em >= data_inicio)
        if data_fim:
            q = q.filter(Alerta.detectado_em <= f"{data_fim} 23:59:59")

        total = q.count()
        alertas = (
            q.order_by(desc(Alerta.detectado_em))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return alertas, total

    # ── Leitura — filtros disponíveis ─────────────────────────────────────

    def listar_ufvs(self) -> list[str]:
        """Valores distintos de UFV para preencher o filtro da tela."""
        rows = (
            self.session
            .query(Alerta.ufv)
            .filter(Alerta.ufv.isnot(None), Alerta.pessoas > 0)
            .distinct()
            .order_by(Alerta.ufv)
            .all()
        )
        return [r.ufv for r in rows]

    def listar_nvrs(self) -> list[dict]:
        """Pares (nvr_id, nvr_nome) distintos para o filtro da tela."""
        rows = (
            self.session
            .query(Alerta.nvr_id, Alerta.nvr_nome)
            .filter(Alerta.pessoas > 0)
            .distinct()
            .order_by(Alerta.nvr_nome)
            .all()
        )
        return [{"nvr_id": r.nvr_id, "nvr_nome": r.nvr_nome} for r in rows]

    # ── Contadores para os cards do topo ──────────────────────────────────

    def resumo(self) -> dict[str, int]:
        """
        Retorna contadores por status para atualização em tempo real.
        Substitui as 4 queries separadas de api_resumo() e central_alarmes().
        """
        rows = (
            self.session
            .query(Alerta.status, func.count(Alerta.id))
            .filter(Alerta.pessoas > 0)
            .group_by(Alerta.status)
            .all()
        )
        base = {
            StatusAlerta.PENDENTE.value:       0,
            StatusAlerta.TRATADO.value:        0,
            StatusAlerta.DETECCAO_FALSA.value: 0,
        }
        for status, count in rows:
            base[status] = count

        total = sum(base.values())
        return {
            "total":            total,
            "pendentes":        base[StatusAlerta.PENDENTE.value],
            "tratados":         base[StatusAlerta.TRATADO.value],
            "deteccoes_falsas": base[StatusAlerta.DETECCAO_FALSA.value],
        }

    # ── Métricas para dashboard ────────────────────────────────────────────

    def alertas_por_dia(self, dias: int = 30) -> list[dict]:
        """Contagem diária de alertas para o gráfico do dashboard."""
        from sqlalchemy import cast, Date
        from datetime import timedelta
        limite = datetime.utcnow() - timedelta(days=dias)
        rows = (
            self.session
            .query(
                cast(Alerta.detectado_em, Date).label("dia"),
                func.count(Alerta.id).label("total"),
            )
            .filter(Alerta.detectado_em >= limite, Alerta.pessoas > 0)
            .group_by("dia")
            .order_by("dia")
            .all()
        )
        return [{"dia": str(r.dia), "total": r.total} for r in rows]

    def top_nvrs_alertas(self, dias: int = 30, limite: int = 5) -> list[dict]:
        """NVRs com mais alertas nos últimos N dias — widget do dashboard."""
        from datetime import timedelta
        corte = datetime.utcnow() - timedelta(days=dias)
        rows = (
            self.session
            .query(Alerta.nvr_nome, func.count(Alerta.id).label("total"))
            .filter(Alerta.detectado_em >= corte, Alerta.pessoas > 0)
            .group_by(Alerta.nvr_nome)
            .order_by(desc("total"))
            .limit(limite)
            .all()
        )
        return [{"nvr": r.nvr_nome, "total": r.total} for r in rows]

"""
repositories/base.py — Classe base para todos os repositories.

Por que injetar sessão em vez de usar db.session diretamente?
──────────────────────────────────────────────────────────────
O motor de ronda (ronda_multi_nvr.py) roda em threads separadas, fora
do Flask request context. Se o repository chamasse `db.session`
diretamente, a thread não teria contexto e levantaria RuntimeError.

Com injeção de sessão:
  • Dentro do Flask (routes/services): não passa nada → usa db.session
  • Fora do Flask (threads do motor): passa uma Session do SQLAlchemy

Uso:
    # Dentro de uma rota Flask (session gerenciada pelo teardown)
    repo = AlertaRepository()
    repo.listar(status="pendente")

    # Dentro de uma thread do motor de ronda
    from sqlalchemy.orm import Session
    from extensions import db
    with db.engine.connect() as conn:
        with Session(bind=conn) as session:
            repo = AlertaRepository(session=session)
            repo.registrar(...)
"""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session


class BaseRepository:
    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        """
        Retorna a sessão injetada ou, se não houver, a sessão do
        contexto Flask atual (db.session é um proxy thread-local).
        """
        if self._session is not None:
            return self._session
        from extensions import db
        return db.session

"""
repositories/db_session.py — Sessão SQLAlchemy fora do Flask context.

Uso exclusivo do motor de ronda (ronda_multi_nvr.py, ronda_loop.py)
que roda em threads separadas, sem Flask request context.

Exemplo:
    from repositories.db_session import session_scope
    from repositories import AlertaRepository, RondaRepository

    with session_scope() as session:
        repo = AlertaRepository(session=session)
        repo.registrar(nvr_id=..., ...)
        # commit automático ao sair do bloco
        # rollback automático em caso de exceção
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# Engine global — preenchida por init_engine() no startup do app.
# Permite uso em threads sem depender do Flask application context.
_engine: Engine | None = None


def init_engine(engine: Engine) -> None:
    """
    Registra a engine SQLAlchemy para uso fora do Flask context.
    Deve ser chamado em app.py logo após db.init_app(app).

    Exemplo em _register_extensions() no app.py:
        from repositories.db_session import init_engine
        db.init_app(app)
        with app.app_context():
            init_engine(db.engine)
    """
    global _engine
    _engine = engine


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager que abre, comita ou reverte uma sessão SQLAlchemy
    sem depender do Flask application context.

    Requer que init_engine() já tenha sido chamado no startup do app.
    Pode ser chamado de qualquer thread após o app estar rodando.
    """
    if _engine is None:
        raise RuntimeError(
            "session_scope() chamado antes de init_engine(). "
            "Certifique-se de chamar init_engine(db.engine) no startup do app."
        )

    session = Session(_engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

"""
repositories/mensagem_repository.py — Acesso a dados de mensagens WhatsApp.

Substitui as queries inline de:
  - whatsapp_routes.py (receber_mensagem, heartbeat, montar_contexto_monitor)
  - services/whatsapp_service.py

Consolida também o StatusSistema (heartbeat do Node.js) que antes ficava
num banco SQLite separado (mensagens.db).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import desc

from models.mensagem import Mensagem, StatusSistema
from .base import BaseRepository


class MensagemRepository(BaseRepository):

    # ── Mensagens ──────────────────────────────────────────────────────────

    def registrar(
        self,
        grupo: str,
        autor: str,
        data: datetime,
        tipo: str,
        conteudo: str,
        alerta: str = "",
    ) -> Mensagem:
        """
        Persiste uma mensagem recebida do conector Node.js.
        Converte string ISO 8601 para datetime se necessário.
        """
        if isinstance(data, str):
            data = datetime.fromisoformat(data.replace("Z", "+00:00"))

        msg = Mensagem(
            grupo=grupo,
            autor=autor,
            data=data,
            tipo=tipo,
            conteudo=conteudo,
            alerta=alerta,
        )
        self.session.add(msg)
        self.session.flush()
        return msg

    def listar_recentes(
        self,
        limite: int = 100,
        grupo: str | None = None,
        apenas_alertas: bool = False,
    ) -> list[Mensagem]:
        q = self.session.query(Mensagem)

        if grupo:
            q = q.filter(Mensagem.grupo == grupo)
        if apenas_alertas:
            q = q.filter(Mensagem.alerta != "")

        return (
            q.order_by(desc(Mensagem.data))
            .limit(limite)
            .all()
        )

    def listar_grupos(self) -> list[str]:
        """Grupos distintos monitorados — para filtros na UI."""
        rows = (
            self.session
            .query(Mensagem.grupo)
            .filter(Mensagem.grupo.isnot(None))
            .distinct()
            .order_by(Mensagem.grupo)
            .all()
        )
        return [r.grupo for r in rows]

    def contar_por_grupo(self, horas: int = 24) -> list[dict]:
        """Mensagens por grupo nas últimas N horas — widget do monitor."""
        from sqlalchemy import func
        corte = datetime.utcnow() - timedelta(hours=horas)
        rows = (
            self.session
            .query(Mensagem.grupo, func.count(Mensagem.id).label("total"))
            .filter(Mensagem.data >= corte)
            .group_by(Mensagem.grupo)
            .order_by(desc("total"))
            .all()
        )
        return [{"grupo": r.grupo, "total": r.total} for r in rows]

    def ultima_mensagem(self) -> Optional[Mensagem]:
        return (
            self.session
            .query(Mensagem)
            .order_by(desc(Mensagem.data))
            .first()
        )

    # ── Status do sistema (heartbeat) ─────────────────────────────────────

    def registrar_heartbeat(self, timestamp: datetime | str | None = None) -> None:
        """
        Atualiza o timestamp do último heartbeat do conector Node.js.
        Cria a linha de status se não existir (id=1).
        """
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                timestamp = datetime.utcnow()

        status = self.session.get(StatusSistema, 1)
        if status is None:
            status = StatusSistema(id=1)
            self.session.add(status)

        status.atualizar(timestamp)

    def status_conector(self) -> dict:
        """
        Retorna estado do conector WhatsApp:
          - online: True se o último heartbeat foi há menos de 2 minutos
          - ultima_verificacao: timestamp ISO ou None
        """
        status = self.session.get(StatusSistema, 1)
        if status is None or status.ultima_verificacao_sistema is None:
            return {"online": False, "ultima_verificacao": None}

        delta = datetime.utcnow() - status.ultima_verificacao_sistema
        return {
            "online": delta.total_seconds() < 120,
            "ultima_verificacao": status.ultima_verificacao_sistema.isoformat(),
        }

"""
repositories/monitor_repository.py — Acesso a dados de monitores.

Substitui as queries diretas de core.py e auth_routes.py.
"""

from __future__ import annotations

from typing import Optional

from models.monitor import Monitor
from .base import BaseRepository


class MonitorRepository(BaseRepository):

    def buscar_por_usuario(self, usuario: str) -> Optional[Monitor]:
        """Retorna o monitor pelo username ou None. Usado no login."""
        return (
            self.session
            .query(Monitor)
            .filter_by(usuario=usuario)
            .first()
        )

    def buscar_por_id(self, monitor_id: int) -> Optional[Monitor]:
        return self.session.get(Monitor, monitor_id)

    def listar_todos(self) -> list[Monitor]:
        return (
            self.session
            .query(Monitor)
            .order_by(Monitor.nome)
            .all()
        )

    def listar_nomes(self) -> list[str]:
        """Retorna lista de nomes — usado em filtros de e-mail/dashboard."""
        rows = (
            self.session
            .query(Monitor.nome)
            .distinct()
            .order_by(Monitor.nome)
            .all()
        )
        return [r.nome for r in rows]

    def criar(
        self,
        nome: str,
        usuario: str,
        senha_plain: str,
        turno: str,
    ) -> Monitor:
        """
        Cria e persiste um novo monitor.
        Lança sqlalchemy.exc.IntegrityError se o usuário já existir.
        """
        monitor = Monitor(nome=nome, usuario=usuario, turno=turno)
        monitor.set_senha(senha_plain)
        self.session.add(monitor)
        self.session.flush()   # gera o ID sem fechar a transação
        return monitor

    def existe_usuario(self, usuario: str) -> bool:
        return (
            self.session
            .query(Monitor.id)
            .filter_by(usuario=usuario)
            .first()
        ) is not None

"""
repositories/nvr_repository.py — CRUD para Nvr e NvrPreset.

Substitui nvr_db.py (SQLite puro).
Segue o padrão do projeto: injeção de session opcional,
fallback para db.session quando não fornecida.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from extensions import db
from models.nvr import Nvr, NvrPreset


class NvrRepository:
    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session or db.session

    # ── Consultas ──────────────────────────────────────────────────────────

    def listar(self, apenas_ativos: bool = False) -> list[Nvr]:
        q = self.session.query(Nvr)
        if apenas_ativos:
            q = q.filter(Nvr.ativo.is_(True))
        return q.order_by(Nvr.nome).all()

    def buscar_por_nvr_id(self, nvr_id: str) -> Nvr | None:
        return self.session.query(Nvr).filter_by(nvr_id=nvr_id).first()

    # ── Criação ────────────────────────────────────────────────────────────

    def criar(
        self,
        nvr_id: str,
        nome: str,
        ip: str,
        usuario: str,
        senha: str,
        ptz_channel: int,
        snapshot_channel: str,
        tempo_espera: int,
        timeout: int,
        ativo: bool,
        presets: dict[int, str],   # {numero: nome}
        site: str = "",
    ) -> Nvr:
        """Cria um novo NVR com seus presets. Lança ValueError se nvr_id já existir."""
        if self.buscar_por_nvr_id(nvr_id):
            raise ValueError(f"PTZ com ID '{nvr_id}' já existe.")

        nvr = Nvr(
            nvr_id=nvr_id,
            nome=nome,
            ip=ip,
            usuario=usuario,
            senha=senha,
            site=site or None,
            ptz_channel=ptz_channel,
            snapshot_channel=snapshot_channel,
            tempo_espera=tempo_espera,
            timeout=timeout,
            ativo=ativo,
        )
        self.session.add(nvr)
        self.session.flush()  # garante nvr.nvr_id disponível para os presets

        self._sincronizar_presets(nvr, presets)
        self.session.commit()
        return nvr

    # ── Atualização ────────────────────────────────────────────────────────

    def atualizar(
        self,
        nvr_id: str,
        nome: str,
        ip: str,
        usuario: str,
        senha: str | None,         # None = manter senha atual
        ptz_channel: int,
        snapshot_channel: str,
        tempo_espera: int,
        timeout: int,
        ativo: bool,
        presets: dict[int, str],
        site: str = "",
    ) -> Nvr:
        nvr = self.buscar_por_nvr_id(nvr_id)
        if not nvr:
            raise ValueError(f"PTZ '{nvr_id}' não encontrada.")

        nvr.nome             = nome
        nvr.ip               = ip
        nvr.usuario          = usuario
        nvr.site             = site or None
        nvr.ptz_channel      = ptz_channel
        nvr.snapshot_channel = snapshot_channel
        nvr.tempo_espera     = tempo_espera
        nvr.timeout          = timeout
        nvr.ativo            = ativo

        if senha:
            nvr.senha = senha

        self._sincronizar_presets(nvr, presets)
        self.session.commit()
        return nvr

    # ── Toggle ativo ───────────────────────────────────────────────────────

    def toggle_ativo(self, nvr_id: str) -> Nvr:
        nvr = self.buscar_por_nvr_id(nvr_id)
        if not nvr:
            raise ValueError(f"PTZ '{nvr_id}' não encontrada.")
        nvr.ativo = not nvr.ativo
        self.session.commit()
        return nvr

    # ── Exclusão ───────────────────────────────────────────────────────────

    def excluir(self, nvr_id: str) -> None:
        nvr = self.buscar_por_nvr_id(nvr_id)
        if nvr:
            self.session.delete(nvr)  # cascade deleta os presets
            self.session.commit()

    # ── Helpers internos ───────────────────────────────────────────────────

    def _sincronizar_presets(self, nvr: Nvr, presets: dict[int, str]) -> None:
        """Substitui todos os presets do NVR pelos fornecidos."""
        # Remove presets existentes
        for p in list(nvr.presets):
            self.session.delete(p)
        self.session.flush()

        # Insere os novos
        for numero, nome in presets.items():
            self.session.add(NvrPreset(nvr_id=nvr.nvr_id, numero=numero, nome=nome))

"""
repositories/ronda_repository.py — Acesso a dados de rondas.

Substitui as queries espalhadas em:
  - core.py (init_db / schema)
  - ronda_multi_nvr.py (salvar_ronda_nvr, atualizar_ronda_pai)
  - ronda_loop.py (_criar_ronda_pai)
  - services/ronda_service.py (queries inline)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import desc

from models.ronda import Ronda, RondaNvr, StatusRonda, StatusRondaNvr
from .base import BaseRepository


class RondaRepository(BaseRepository):

    # ── Ronda pai ──────────────────────────────────────────────────────────

    def criar(
        self,
        monitor_id: int,
        monitor_nome: str,
        turno: str,
        pasta: str,
    ) -> Ronda:
        """
        Cria uma ronda pai com status em_andamento.
        Usado pelo ronda_loop.py e pelo RondaService.
        """
        ronda = Ronda(
            monitor_id=monitor_id,
            monitor_nome=monitor_nome,
            turno=turno,
            pasta=pasta,
            iniciada_em=datetime.utcnow(),
            status=StatusRonda.EM_ANDAMENTO.value,
        )
        self.session.add(ronda)
        self.session.flush()   # gera o ID imediatamente
        return ronda

    def buscar_por_id(self, ronda_id: int) -> Optional[Ronda]:
        return self.session.get(Ronda, ronda_id)

    def listar_historico(self, limite: int = 200) -> list[Ronda]:
        """Retorna as N rondas mais recentes para a tela de histórico."""
        return (
            self.session
            .query(Ronda)
            .order_by(desc(Ronda.iniciada_em))
            .limit(limite)
            .all()
        )

    def listar_filtrado(
        self,
        data_ini: str | None = None,
        data_fim: str | None = None,
        turno: str | None = None,
        monitor_nome: str | None = None,
        status: str | None = None,
        limite: int = 200,
    ) -> list[Ronda]:
        """
        Listagem com filtros opcionais — usada pela rota de e-mail
        e por relatórios customizados.
        """
        q = self.session.query(Ronda)

        if data_ini:
            q = q.filter(Ronda.iniciada_em >= data_ini)
        if data_fim:
            q = q.filter(Ronda.iniciada_em <= f"{data_fim} 23:59:59")
        if turno:
            q = q.filter(Ronda.turno == turno)
        if monitor_nome:
            q = q.filter(Ronda.monitor_nome == monitor_nome)
        if status:
            q = q.filter(Ronda.status == status)

        return (
            q.order_by(desc(Ronda.iniciada_em))
            .limit(limite)
            .all()
        )

    def finalizar(
        self,
        ronda_id: int,
        status: StatusRonda = StatusRonda.FINALIZADA,
    ) -> None:
        """
        Atualiza status e finalizada_em da ronda pai.
        Substitui atualizar_ronda_pai() de ronda_multi_nvr.py.
        """
        ronda = self.session.get(Ronda, ronda_id)
        if ronda:
            ronda.finalizar(status)

    # ── Ronda NVR ─────────────────────────────────────────────────────────

    def registrar_nvr(
        self,
        ronda_id: int | None,
        nvr_id: str,
        nvr_nome: str,
        status: str,
        invasoes: int,
        pasta: str,
    ) -> RondaNvr:
        """
        Salva o resultado de um NVR ao final da sua thread.
        Substitui salvar_ronda_nvr() de ronda_multi_nvr.py.
        """
        nvr = RondaNvr(
            ronda_id=ronda_id,
            nvr_id=nvr_id,
            nvr_nome=nvr_nome,
            status=status,
            invasoes=invasoes,
            pasta=pasta,
            finalizada_em=datetime.utcnow(),
        )
        self.session.add(nvr)
        self.session.flush()
        return nvr

    def listar_nvrs_por_ronda(self, ronda_id: int) -> list[RondaNvr]:
        return (
            self.session
            .query(RondaNvr)
            .filter_by(ronda_id=ronda_id)
            .all()
        )

    # ── Métricas para dashboard ────────────────────────────────────────────

    def contar_por_status(self) -> dict[str, int]:
        """Retorna {status: contagem} para todos os status existentes."""
        from sqlalchemy import func
        rows = (
            self.session
            .query(Ronda.status, func.count(Ronda.id))
            .group_by(Ronda.status)
            .all()
        )
        return {status: count for status, count in rows}

    def total_por_monitor(self, dias: int = 30) -> list[dict]:
        """Rondas agrupadas por monitor nos últimos N dias."""
        from sqlalchemy import func
        from datetime import timedelta
        limite = datetime.utcnow() - timedelta(days=dias)
        rows = (
            self.session
            .query(Ronda.monitor_nome, func.count(Ronda.id).label("total"))
            .filter(Ronda.iniciada_em >= limite)
            .group_by(Ronda.monitor_nome)
            .order_by(desc("total"))
            .all()
        )
        return [{"monitor": r.monitor_nome, "total": r.total} for r in rows]

    def rondas_por_dia(self, dias: int = 30) -> list[dict]:
        """Contagem diária de rondas para o gráfico do dashboard."""
        from sqlalchemy import func, cast, Date
        from datetime import timedelta
        limite = datetime.utcnow() - timedelta(days=dias)
        rows = (
            self.session
            .query(
                cast(Ronda.iniciada_em, Date).label("dia"),
                func.count(Ronda.id).label("total"),
            )
            .filter(Ronda.iniciada_em >= limite)
            .group_by("dia")
            .order_by("dia")
            .all()
        )
        return [{"dia": str(r.dia), "total": r.total} for r in rows]
