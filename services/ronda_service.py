"""
services/ronda_service.py — Orquestração de rondas.

Responsabilidades:
  - Criar rondas (simples e multi-NVR) via RondaRepository
  - Disparar o script de ronda em background (subprocess)
  - Montar contextos para as rotas de histórico e relatório
  - Gerenciar monitores via MonitorRepository

Não importa sqlite3, get_db, nvr_config nem queries SQL — apenas repositórios.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sqlalchemy.exc import IntegrityError

BASE_DIR = Path(__file__).resolve().parent.parent
RELATORIOS_DIR = BASE_DIR / "relatorios"

from repositories.monitor_repository import MonitorRepository
from repositories.nvr_repository import NvrRepository
from repositories.ronda_repository import RondaRepository


class RondaService:
    """Orquestra criação, consulta e execução de rondas."""

    def __init__(
        self,
        ronda_repo: RondaRepository | None = None,
        monitor_repo: MonitorRepository | None = None,
        nvr_repo: NvrRepository | None = None,
    ) -> None:
        self._ronda_repo   = ronda_repo   or RondaRepository()
        self._monitor_repo = monitor_repo or MonitorRepository()
        self._nvr_repo     = nvr_repo     or NvrRepository()

    # ── Iniciar rondas ─────────────────────────────────────────────────────

    def iniciar_ronda(self, monitor_id: int, monitor_nome: str, turno: str) -> int:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pasta = f"relatorios/ronda_{timestamp}"

        ronda = self._ronda_repo.criar(monitor_id, monitor_nome, turno, pasta)

        self._executar_background(
            "ronda.py",
            "--monitor", monitor_nome,
            "--turno", turno,
            "--pasta", pasta,
            "--ronda-id", str(ronda.id),
        )
        return ronda.id

    def iniciar_ronda_multi(
        self,
        monitor_id: int,
        monitor_nome: str,
        turno: str,
        nvr_ids: list[str] | None = None,
    ) -> int:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pasta = str(RELATORIOS_DIR / f"multi_{timestamp}")

        ronda = self._ronda_repo.criar(monitor_id, monitor_nome, turno, pasta)

        args = [
            "--monitor", monitor_nome,
            "--turno", turno,
            "--pasta", pasta,
            "--ronda-id", str(ronda.id),
        ]
        if nvr_ids:
            args.extend(["--nvrs", *nvr_ids])

        self._executar_background("ronda_multi_nvr.py", *args)
        return ronda.id

    # ── Consultas ──────────────────────────────────────────────────────────

    def listar_historico(self):
        return self._ronda_repo.listar_historico()

    def buscar_ronda(self, ronda_id: int):
        return self._ronda_repo.buscar_por_id(ronda_id)

    def status_ronda(self, ronda_id: int) -> tuple[dict, int]:
        ronda = self._ronda_repo.buscar_por_id(ronda_id)
        if not ronda:
            return {"erro": "Ronda não encontrada"}, 404

        nvrs = self._ronda_repo.listar_nvrs_por_ronda(ronda_id)
        return {
            "status": ronda.status,
            "nvrs": [
                {
                    "nvr_id":   item.nvr_id,
                    "nvr_nome": item.nvr_nome,
                    "status":   item.status,
                    "invasoes": item.invasoes,
                }
                for item in nvrs
            ],
        }, 200

    def montar_relatorio_multi_context(self, ronda_id: int) -> dict | None:
        ronda = self._ronda_repo.buscar_por_id(ronda_id)
        if not ronda:
            return None

        pasta_path = BASE_DIR / Path(ronda.pasta)
        dados      = self._carregar_dados_relatorio(pasta_path)
        pasta_name = Path(ronda.pasta).name

        return {
            "ronda":      ronda,
            "dados":      dados,
            "pasta_name": pasta_name,
            "img_prefix": f"/relatorios/{pasta_name}/imagens/",
        }

    # ── Monitores ──────────────────────────────────────────────────────────

    def listar_monitores(self):
        return self._monitor_repo.listar_todos()

    def cadastrar_monitor(self, nome: str, usuario: str, senha: str, turno: str) -> tuple[bool, str]:
        if self._monitor_repo.existe_usuario(usuario):
            return False, f"Usuário '{usuario}' já cadastrado."
        try:
            self._monitor_repo.criar(nome, usuario, senha, turno)
            return True, ""
        except IntegrityError:
            return False, "Erro de integridade ao cadastrar monitor."

    # ── NVRs ───────────────────────────────────────────────────────────────

    def quantidade_nvrs(self, nvr_ids: list[str] | None) -> int:
        """Retorna quantos NVRs serão processados na ronda."""
        if nvr_ids:
            return len(nvr_ids)
        return len(self._nvr_repo.listar(apenas_ativos=True))

    # ── Internos ───────────────────────────────────────────────────────────

    def _executar_background(self, script_name: str, *args: str) -> None:
        subprocess.Popen(
            [sys.executable, str(BASE_DIR / script_name), *args],
            cwd=BASE_DIR,
        )

    @staticmethod
    def _carregar_dados_relatorio(pasta_path: Path) -> dict | None:
        for nome_json in ("dados_multi.json", "dados.json"):
            json_path = pasta_path / nome_json
            if not json_path.exists():
                continue
            try:
                return json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None
