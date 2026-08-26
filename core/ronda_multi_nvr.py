"""
core/ronda_multi_nvr.py — Motor de Ronda Paralela para múltiplos NVRs.

Executa rondas em até 5 NVRs simultaneamente usando ThreadPoolExecutor.
Cada NVR roda em sua própria thread: move PTZ → snapshot → YOLO → salva resultado.
Ao final, consolida um relatório HTML unificado e atualiza o banco de dados.

Mudanças em relação à versão SQLite:
  - salvar_ronda_nvr()   → RondaRepository.registrar_nvr()
  - atualizar_ronda_pai() → RondaRepository.finalizar()
  - registrar_alerta()   → AlertaRepository.registrar()
  Todas as operações de banco usam session_scope() — seguro para threads.

Uso:
    python -m core.ronda_multi_nvr --monitor "Nome" --turno "Diurno"
    python -m core.ronda_multi_nvr --monitor "Nome" --turno "Noturno" --nvrs nvr_01 nvr_03
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
import threading

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import cv2
import requests
from dotenv import load_dotenv
from jinja2 import Template
from requests.auth import HTTPDigestAuth
from ultralytics import YOLO

from dataclasses import dataclass, field
from typing import Dict

@dataclass
class NVRConfig:
    """Config local de NVR — espelha models.nvr.Nvr para compatibilidade."""
    id: str
    nome: str
    ip: str
    usuario: str
    senha: str
    ptz_channel: int = 1
    snapshot_channel: str = "501"
    presets: Dict[int, str] = field(default_factory=dict)
    tempo_espera: int = 5
    timeout: int = 10
    site: str = ""
    ativo: bool = True


def _nvr_para_config(nvr) -> NVRConfig:
    """
    Converte objeto Nvr (SQLAlchemy) para NVRConfig (dataclass).

    Usa getattr com fallback para ptz_channel porque o model Nvr pode não
    ter essa coluna definida (ou ter outro nome, ex: canal_ptz). Sem essa
    proteção, qualquer NVR cadastrado sem esse atributo quebra a ronda
    inteira com AttributeError, impedindo o PTZ de se mover entre presets
    e fazendo a câmera repetir sempre a mesma imagem.
    """
    ptz_channel = getattr(nvr, "ptz_channel", None)
    if ptz_channel is None:
        ptz_channel = getattr(nvr, "canal_ptz", 1)  # nome alternativo possível

    snapshot_channel = getattr(nvr, "snapshot_channel", None)
    if snapshot_channel is None:
        snapshot_channel = getattr(nvr, "canal_snapshot", "501")

    return NVRConfig(
        id=nvr.nvr_id,
        nome=nvr.nome,
        ip=nvr.ip,
        usuario=nvr.usuario,
        senha=nvr.senha,
        ptz_channel=ptz_channel,
        snapshot_channel=snapshot_channel,
        presets={p.numero: p.nome for p in nvr.presets},
        tempo_espera=nvr.tempo_espera,
        timeout=nvr.timeout,
        site=nvr.site or "",
        ativo=nvr.ativo,
    )
from core.yolo_config import caminho_modelo_yolo
from core.analisar_imagem import analisar_imagem

load_dotenv()

# =========================================================
# CONFIGURAÇÕES YOLO
# =========================================================

MODELO_YOLO = caminho_modelo_yolo()

_model_lock = threading.Lock()


def detectar_device() -> str:
    """
    Detecta automaticamente se há GPU NVIDIA (CUDA) disponível.
    Sobrescrever via variável de ambiente YOLO_DEVICE (ex: "cpu", "cuda:0").
    """
    device_env = os.getenv("YOLO_DEVICE", "").strip()
    if device_env:
        return device_env
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:0"
    except ImportError:
        pass
    return "cpu"


DEVICE = detectar_device()
USAR_FP16 = DEVICE.startswith("cuda")


def get_model() -> YOLO:
    """
    Retorna nova instância YOLO por thread, já no dispositivo correto.
    Conforme documentação Ultralytics: cada thread deve ter sua própria
    instância — nunca compartilhe objetos YOLO entre threads.
    """
    model = YOLO(MODELO_YOLO)
    if DEVICE.startswith("cuda"):
        # Pré-aquece a GPU — primeira inferência em CUDA é mais lenta
        # (compilação de kernels); fazer isso fora do loop de presets
        # evita que o preset 1 pague esse custo sozinho.
        import numpy as np
        dummy = np.zeros((640, 640, 3), dtype="uint8")
        model(dummy, imgsz=640, verbose=False, device=DEVICE)
    return model


# =========================================================
# TEMPLATE HTML CONSOLIDADO
# =========================================================

TEMPLATE_MULTI = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <title>Relatório Multi-NVR — {{ data }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0d1117;
            color: #e6edf3;
            padding: 32px;
        }
        h1 { font-size: 1.6rem; color: #58a6ff; margin-bottom: 4px; }
        .meta { font-size: 13px; color: #8b949e; margin-bottom: 28px; }
        .nvr-bloco {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            margin-bottom: 32px;
            overflow: hidden;
        }
        .nvr-header {
            background: #1f2937;
            padding: 14px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .nvr-header h2 { font-size: 1rem; color: #f0f6fc; }
        .badge {
            font-size: 11px;
            font-weight: bold;
            padding: 3px 10px;
            border-radius: 20px;
        }
        .badge.ok     { background: #1a4731; color: #3fb950; }
        .badge.alerta { background: #4a2c0a; color: #f0883e; }
        .badge.erro   { background: #3d1c1e; color: #f85149; }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: #21262d;
            padding: 10px 14px;
            font-size: 12px;
            color: #8b949e;
            text-align: left;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        td {
            padding: 10px 14px;
            border-bottom: 1px solid #21262d;
            font-size: 13px;
            vertical-align: middle;
        }
        tr:last-child td { border-bottom: none; }
        tr.alerta { background: rgba(240,136,62,0.07); }
        .status-ok     { color: #3fb950; font-weight: bold; }
        .status-alerta { color: #f85149; font-weight: bold; }
        img { width: 280px; border-radius: 6px; border: 1px solid #30363d; }
        .resumo {
            display: flex;
            gap: 20px;
            padding: 16px 20px;
            border-top: 1px solid #30363d;
            font-size: 13px;
            color: #8b949e;
        }
        .resumo span { color: #e6edf3; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🛰️ Relatório de Ronda Multi-NVR</h1>
    <div class="meta">
        Data: {{ data }} &nbsp;|&nbsp;
        Monitor: {{ monitor_nome }} &nbsp;|&nbsp;
        Turno: {{ turno }} &nbsp;|&nbsp;
        NVRs processados: {{ nvrs | length }}
    </div>

    {% for nvr in nvrs %}
    <div class="nvr-bloco">
        <div class="nvr-header">
            <h2>📷 {{ nvr.nome }} ({{ nvr.ip }})</h2>
            {% if nvr.invasoes > 0 %}
                <span class="badge alerta">⚠️ {{ nvr.invasoes }} INVASÃO(ÕES)</span>
            {% elif nvr.erro %}
                <span class="badge erro">❌ ERRO</span>
            {% else %}
                <span class="badge ok">✅ NORMAL</span>
            {% endif %}
        </div>

        {% if nvr.erro %}
        <div style="padding:16px 20px; color:#f85149;">
            Falha ao processar este NVR: {{ nvr.erro }}
        </div>
        {% else %}
        <table>
            <tr>
                <th>Horário</th>
                <th>Local (Preset)</th>
                <th>Status</th>
                <th>Pessoas</th>
                <th>Imagem</th>
            </tr>
            {% for linha in nvr.linhas %}
            <tr class="{{ linha.classe_css }}">
                <td>{{ linha.horario }}</td>
                <td>{{ linha.nome_local }}</td>
                <td class="{{ 'status-alerta' if linha.pessoas > 0 else 'status-ok' }}">
                    {{ linha.status }}
                </td>
                <td>{{ linha.pessoas }}</td>
                <td>
                    <img src="{{ nvr.id }}/imagens/{{ linha.nome_local }}.jpg"
                         onerror="this.style.display='none'">
                </td>
            </tr>
            {% endfor %}
        </table>
        <div class="resumo">
            Presets percorridos: <span>{{ nvr.linhas | length }}</span>
            &nbsp;|&nbsp; Invasões detectadas: <span>{{ nvr.invasoes }}</span>
            &nbsp;|&nbsp; Duração: <span>{{ nvr.duracao_s }}s</span>
        </div>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
"""


# =========================================================
# LOGGING
# =========================================================

def criar_logger(nvr_id: str, pasta: Path) -> logging.Logger:
    logger = logging.getLogger(nvr_id)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    fmt = logging.Formatter(f"%(asctime)s [{nvr_id}] [%(levelname)s] %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(pasta / f"{nvr_id}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# =========================================================
# BANCO DE DADOS — via repositories (sem sqlite3)
# =========================================================

def _salvar_ronda_nvr(
    ronda_pai_id: int | None,
    nvr_id: str,
    nvr_nome: str,
    status: str,
    invasoes: int,
    pasta: str,
) -> None:
    """
    Persiste resultado do NVR usando RondaRepository + session_scope().
    Substitui salvar_ronda_nvr() com sqlite3 direto.
    Seguro para threads — cada chamada abre e fecha sua própria sessão.
    """
    try:
        from repositories.db_session import session_scope
        from repositories.ronda_repository import RondaRepository
        with session_scope() as session:
            RondaRepository(session=session).registrar_nvr(
                ronda_id=ronda_pai_id,
                nvr_id=nvr_id,
                nvr_nome=nvr_nome,
                status=status,
                invasoes=invasoes,
                pasta=pasta,
            )
    except Exception as e:
        print(f"[AVISO DB] salvar_ronda_nvr: {e}")


def _atualizar_ronda_pai(ronda_id: int | None, status: str) -> None:
    """
    Atualiza status da ronda pai usando RondaRepository + session_scope().
    Substitui atualizar_ronda_pai() com sqlite3 direto.
    """
    if not ronda_id:
        return
    try:
        from repositories.db_session import session_scope
        from repositories.ronda_repository import RondaRepository
        from models.ronda import StatusRonda
        with session_scope() as session:
            RondaRepository(session=session).finalizar(
                ronda_id=ronda_id,
                status=StatusRonda(status),
            )
    except Exception as e:
        print(f"[AVISO DB] atualizar_ronda_pai: {e}")


def _registrar_alerta(
    ronda_id: int | None,
    nvr_id: str,
    nvr_nome: str,
    ufv: str | None,
    local_preset: str,
    pessoas: int,
    imagem_path: str | None,
    detectado_em: datetime,
) -> None:
    """
    Registra alerta na Central de Alarmes usando AlertaRepository + session_scope().
    Substitui registrar_alerta() de alarmes_schema.py.
    """
    try:
        from repositories.db_session import session_scope
        from repositories.alerta_repository import AlertaRepository
        with session_scope() as session:
            AlertaRepository(session=session).registrar(
                ronda_id=ronda_id,
                nvr_id=nvr_id,
                nvr_nome=nvr_nome,
                ufv=ufv,
                local_preset=local_preset,
                pessoas=pessoas,
                imagem_path=imagem_path,
                detectado_em=detectado_em,
            )
    except Exception as e:
        print(f"[AVISO DB] registrar_alerta: {e}")


# =========================================================
# SESSÃO HTTP
# =========================================================

def criar_sessao(cfg: NVRConfig) -> requests.Session:
    s = requests.Session()
    s.auth = HTTPDigestAuth(cfg.usuario, cfg.senha)
    return s


def testar_autenticacao(
    sessao: requests.Session, cfg: NVRConfig, log: logging.Logger
) -> bool:
    url = f"http://{cfg.ip}/ISAPI/System/deviceInfo"
    try:
        r = sessao.get(url, timeout=cfg.timeout)
        if r.status_code == 200:
            log.info("Autenticado com sucesso.")
            return True
        log.error("Falha auth. Status: %s", r.status_code)
        return False
    except requests.RequestException as e:
        log.error("Erro de conexão: %s", e)
        return False


# =========================================================
# PTZ
# =========================================================

def mover_ptz(
    sessao: requests.Session,
    cfg: NVRConfig,
    preset: int,
    log: logging.Logger,
) -> bool:
    url = (
        f"http://{cfg.ip}/ISAPI/PTZCtrl/channels/"
        f"{cfg.ptz_channel}/presets/{preset}/goto"
    )
    try:
        r = sessao.put(url, timeout=cfg.timeout)
        ok = r.status_code == 200
        if ok:
            log.info("PTZ → preset %d OK.", preset)
        else:
            log.error("PTZ falhou. Status: %s", r.status_code)
        return ok
    except requests.RequestException as e:
        log.error("Erro PTZ: %s", e)
        return False


# =========================================================
# SNAPSHOT
# =========================================================

def capturar_snapshot(
    sessao: requests.Session,
    cfg: NVRConfig,
    pasta_imagens: Path,
    nome_local: str,
    log: logging.Logger,
) -> Path | None:
    url = (
        f"http://{cfg.ip}/ISAPI/Streaming/channels/"
        f"{cfg.snapshot_channel}/picture"
    )
    try:
        r = sessao.get(url, timeout=cfg.timeout, stream=True)
        if r.status_code != 200:
            log.error("Snapshot falhou. Status: %s", r.status_code)
            return None
        caminho = pasta_imagens / f"{nome_local}.jpg"
        with open(caminho, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        log.info("Snapshot salvo: %s", caminho.name)
        return caminho
    except requests.RequestException as e:
        log.error("Erro snapshot: %s", e)
        return None

# =========================================================
# RONDA DE UM ÚNICO NVR (roda em thread própria)
# =========================================================
#
# NOTA: as funções remover_overlays(), filtrar_deteccoes_tile() e
# analisar_imagem() antigas foram REMOVIDAS daqui. Agora vêm de
# core/analisar_imagem.py, importado no topo do arquivo:
#
#     from core.analisar_imagem import analisar_imagem
#
# Se essa linha de import não estiver no topo do seu ronda_multi_nvr.py,
# adicione antes de colar este bloco — senão vai dar
# NameError: name 'analisar_imagem' is not defined.

def executar_ronda_nvr(
    cfg: NVRConfig,
    pasta_raiz: Path,
    ronda_pai_id: int | None,
    log_global: logging.Logger,
) -> dict:
    t_inicio   = time.time()
    pasta_nvr  = pasta_raiz / cfg.id
    pasta_imgs = pasta_nvr / "imagens"
    pasta_imgs.mkdir(parents=True, exist_ok=True)

    log = criar_logger(cfg.id, pasta_nvr)
    log.info("=== INICIANDO RONDA | NVR: %s | IP: %s ===", cfg.nome, cfg.ip)

    sessao = criar_sessao(cfg)
    model  = get_model()  # uma instância por thread/NVR, reaproveitada em todos os presets

    if not testar_autenticacao(sessao, cfg, log):
        log.error("Falha na autenticação. Abortando NVR.")
        _salvar_ronda_nvr(ronda_pai_id, cfg.id, cfg.nome, "erro", 0, str(pasta_nvr))
        return {
            "id": cfg.id, "nome": cfg.nome, "ip": cfg.ip,
            "erro": "Falha de autenticação",
            "linhas": [], "invasoes": 0,
            "duracao_s": int(time.time() - t_inicio),
        }

    linhas   = []
    invasoes = 0

    for preset, nome_local in cfg.presets.items():
        log.info("--- Preset %d: %s ---", preset, nome_local)

        if not mover_ptz(sessao, cfg, preset, log):
            log.warning("Pulando '%s': falha PTZ.", nome_local)
            continue

        log.info("Aguardando estabilização (%ds)...", cfg.tempo_espera)
        time.sleep(cfg.tempo_espera)

        imagem = capturar_snapshot(sessao, cfg, pasta_imgs, nome_local, log)
        if imagem is None:
            continue

        pessoas, imagem_anotada = analisar_imagem(imagem, model, DEVICE, log)
        invasoes += pessoas

        if pessoas > 0:
            try:
                try:
                    pasta_rel = pasta_raiz.relative_to(Path("relatorios"))
                except ValueError:
                    pasta_rel = pasta_raiz

                nome_img = imagem_anotada.name if imagem_anotada else f"{nome_local}.jpg"
                imagem_path_banco = (
                    pasta_rel / cfg.id / "imagens" / nome_img
                ).as_posix()

                _registrar_alerta(
                    ronda_id=ronda_pai_id,
                    nvr_id=cfg.id,
                    nvr_nome=cfg.nome,
                    ufv=getattr(cfg, "site", None),   # NVRConfig usa "site", não "ufv"
                    local_preset=nome_local,
                    pessoas=pessoas,
                    imagem_path=imagem_path_banco,
                    detectado_em=datetime.now(),
                )
                log.info("Alerta registrado: %s (%d pessoa(s))", nome_local, pessoas)
            except Exception as e:
                log.warning("Não foi possível registrar alerta: %s", e)

        linhas.append({
            "horario":    datetime.now().strftime("%H:%M:%S"),
            "nome_local": nome_local,
            "status":     "INVASÃO DETECTADA" if pessoas > 0 else "NORMAL",
            "classe_css": "alerta" if pessoas > 0 else "normal",
            "pessoas":    pessoas,
        })

    duracao      = int(time.time() - t_inicio)
    status_final = "com_alertas" if invasoes > 0 else "finalizada"
    _salvar_ronda_nvr(ronda_pai_id, cfg.id, cfg.nome, status_final, invasoes, str(pasta_nvr))

    log.info("=== RONDA NVR FINALIZADA | Invasões: %d | Duração: %ds ===",
             invasoes, duracao)

    return {
        "id":        cfg.id,
        "nome":      cfg.nome,
        "ip":        cfg.ip,
        "erro":      None,
        "linhas":    linhas,
        "invasoes":  invasoes,
        "duracao_s": duracao,
    }

# =========================================================
# RELATÓRIO HTML CONSOLIDADO
# =========================================================

def gerar_relatorio_multi(
    pasta_raiz: Path,
    resultados: list[dict],
    monitor_nome: str,
    turno: str,
) -> Path:
    conteudo = Template(TEMPLATE_MULTI).render(
        data=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        monitor_nome=monitor_nome,
        turno=turno,
        nvrs=resultados,
    )
    arquivo = pasta_raiz / "relatorio_multi.html"
    arquivo.write_text(conteudo, encoding="utf-8")

    dados_json = pasta_raiz / "dados_multi.json"
    dados_json.write_text(
        json.dumps({
            "data":         datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "monitor_nome": monitor_nome,
            "turno":        turno,
            "nvrs":         resultados,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return arquivo


# =========================================================
# ORQUESTRADOR PRINCIPAL
# =========================================================

def executar_ronda_multi(
    monitor_nome: str = "Não informado",
    turno: str = "Não informado",
    pasta: str | None = None,
    ronda_id: int | None = None,
    nvr_ids: list[str] | None = None,
    max_workers: int | None = None,
) -> None:
    from repositories.db_session import session_scope
    from repositories.nvr_repository import NvrRepository
    filtros = set(nvr_ids or [])
    with session_scope() as session:
        todos = NvrRepository(session=session).listar(apenas_ativos=True)
        if filtros:
            nvrs_db = [n for n in todos if n.nvr_id in filtros or (n.site or "") in filtros or n.nome in filtros]
        else:
            nvrs_db = todos
        nvrs_selecionados = [_nvr_para_config(n) for n in nvrs_db]

    if not nvrs_selecionados:
        print("❌ Nenhum NVR válido selecionado.")
        return

    # max_workers dinâmico: 1 thread por dome, sem teto artificial de 5.
    # Antes, com 6 domes e max_workers=5, a 6ª dome ficava esperando uma
    # vaga liberar de outra já em andamento — adicionando até ~2 minutos
    # de espera improdutiva ao ciclo. Agora cada dome roda sua própria
    # thread desde o início.
    if max_workers is None:
        max_workers = len(nvrs_selecionados)

    timestamp  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pasta_raiz = Path(pasta) if pasta else Path("relatorios") / f"multi_{timestamp}"
    pasta_raiz.mkdir(parents=True, exist_ok=True)

    log_global = criar_logger("MULTI", pasta_raiz)
    log_global.info(
        "=== RONDA MULTI-NVR | Monitor: %s | Turno: %s | NVRs: %d ===",
        monitor_nome, turno, len(nvrs_selecionados),
    )
    log_global.info(
        "YOLO device=%s | half(FP16)=%s | max_workers=%d",
        DEVICE, USAR_FP16, max_workers,
    )

    resultados_ordenados = []
    futuros = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for cfg in nvrs_selecionados:
            f = executor.submit(
                executar_ronda_nvr, cfg, pasta_raiz, ronda_id, log_global
            )
            futuros[f] = cfg.id

        for futuro in as_completed(futuros):
            nvr_id_key = futuros[futuro]
            try:
                resultado = futuro.result()
                resultados_ordenados.append(resultado)
                log_global.info(
                    "✅ NVR %s concluído | Invasões: %d",
                    resultado["nome"], resultado["invasoes"],
                )
            except Exception as e:
                log_global.error("❌ NVR %s lançou exceção: %s", nvr_id_key, e)
                resultados_ordenados.append({
                    "id": nvr_id_key, "nome": nvr_id_key, "ip": "?",
                    "erro": str(e), "linhas": [], "invasoes": 0, "duracao_s": 0,
                })

    ordem = {cfg.id: i for i, cfg in enumerate(nvrs_selecionados)}
    resultados_ordenados.sort(key=lambda r: ordem.get(r["id"], 999))

    arquivo_html = gerar_relatorio_multi(
        pasta_raiz, resultados_ordenados, monitor_nome, turno
    )

    total_invasoes = sum(r["invasoes"] for r in resultados_ordenados)
    nvrs_ok = [r for r in resultados_ordenados if not r.get("erro")]
    status_pai = ("com_alertas" if total_invasoes > 0 else "finalizada") if nvrs_ok else "erro"
    _atualizar_ronda_pai(ronda_id, status_pai)

    log_global.info("=== MULTI-RONDA FINALIZADA ===")
    log_global.info("Invasões totais: %d", total_invasoes)
    log_global.info("Relatório: %s", arquivo_html)
    print(f"\n✅ Ronda finalizada. Relatório: {arquivo_html}")


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ronda Multi-NVR Paralela")
    parser.add_argument("--monitor",  default="Não informado")
    parser.add_argument("--turno",    default="Não informado")
    parser.add_argument("--pasta",    default=None)
    parser.add_argument("--ronda-id", default=None, type=int)
    parser.add_argument("--nvrs",     nargs="*", default=None,
                        help="IDs dos NVRs (ex: nvr_01 nvr_03). Omitir = todos.")
    parser.add_argument("--workers",  default=None, type=int,
                        help="Threads simultâneas. Omitir = 1 por dome selecionada.")
    args = parser.parse_args()

    executar_ronda_multi(
        monitor_nome=args.monitor,
        turno=args.turno,
        pasta=args.pasta,
        ronda_id=args.ronda_id,
        nvr_ids=args.nvrs,
        max_workers=args.workers,
    )
