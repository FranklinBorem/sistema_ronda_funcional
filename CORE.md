# sistema_ronda_funcional

## Pasta Core 

"""
core/analisar_imagem.py — Motor de análise YOLO refatorado.

Substitui as funções analisar_imagem(), filtrar_deteccoes_tile() e
remover_overlays() de ronda_multi_nvr.py, centralizando toda a lógica
de inferência e pós-processamento aqui.

Usa os parâmetros de yolo_config.py — ajuste lá, não aqui.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from core.yolo_config import FILTRO, TILING, YOLO_PARAMS


def remover_overlays(img: np.ndarray) -> np.ndarray:
    """
    Zera regiões da imagem que contêm overlays da câmera (data/hora, logo).
    Configurável via FILTRO em yolo_config.py.
    """
    h, w = img.shape[:2]
    topo   = FILTRO["remover_topo_frac"]
    rodape = FILTRO["remover_rodape_frac"]
    rod_x  = FILTRO["remover_rodape_x_frac"]

    img[: int(h * topo), :] = 0
    img[int(h * rodape) :, int(w * rod_x) :] = 0
    return img


def _filtrar_deteccoes(
    deteccoes_brutas: list[tuple],
    largura_img: int,
    altura_img: int,
) -> list[dict]:
    """
    Aplica filtros geométricos sobre as detecções brutas do YOLO.
    Elimina falsos positivos que passaram da confiança mínima.
    """
    topo   = FILTRO["remover_topo_frac"]
    rodape = FILTRO["remover_rodape_frac"]
    rod_x  = FILTRO["remover_rodape_x_frac"]
    area_min  = FILTRO["area_minima"]
    larg_min  = FILTRO["largura_minima"]
    alt_min   = FILTRO["altura_minima"]
    ar_min    = FILTRO["aspect_ratio_min"]

    validas = []
    for x1, y1, x2, y2, conf, origem in deteccoes_brutas:
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        # Remove detecções nos overlays da câmera
        if cy < altura_img * topo:
            continue
        if cx > largura_img * rod_x and cy > altura_img * rodape:
            continue

        larg = x2 - x1
        alt  = y2 - y1
        area = larg * alt
        ar   = alt / max(larg, 1)

        if area < area_min or larg < larg_min:
            continue
        if alt < alt_min or ar < ar_min:
            continue

        validas.append({
            "bbox":         (x1, y1, x2, y2),
            "confianca":    conf,
            "area":         area,
            "largura":      larg,
            "altura":       alt,
            "aspect_ratio": ar,
            "origem":       origem,
        })
    return validas


def analisar_imagem(
    caminho_imagem: Path,
    model,
    device: str,
    log: logging.Logger,
) -> tuple[int, Path | None]:
    """
    Analisa uma imagem e retorna (n_pessoas, caminho_imagem_anotada).

    Fluxo:
      1. Lê a imagem com OpenCV
      2. Remove overlays da câmera
      3. Inferência na imagem inteira (imgsz alto)
      4. Tiling 3x3 com sobreposição (detecta pessoas distantes/pequenas)
      5. Filtro geométrico pós-YOLO
      6. Anotação e salvamento da imagem se houver detecções

    Args:
        caminho_imagem: Path para o JPEG do snapshot
        model: instância YOLO já carregada (por thread)
        device: "cuda:0" ou "cpu"
        log: logger da thread do NVR

    Returns:
        (n_pessoas, path_anotado) — path_anotado é None se não houver detecções
    """
    img_original = cv2.imread(str(caminho_imagem))
    if img_original is None:
        log.error("Não foi possível ler: %s", caminho_imagem)
        return 0, None

    img_analise = remover_overlays(img_original.copy())
    altura, largura = img_analise.shape[:2]
    deteccoes_brutas: list[tuple] = []

    # ── 1. Inferência na imagem inteira ──────────────────────────────────
    log.info("YOLO — imagem inteira (imgsz=%d, conf=%.2f)...",
             YOLO_PARAMS["imgsz"], YOLO_PARAMS["conf"])

    res = model(
        img_analise,
        device=device,
        **YOLO_PARAMS,
    )
    for r in res:
        for box in r.boxes:
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            deteccoes_brutas.append((x1, y1, x2, y2, conf, "inteira"))

    # ── 2. Tiling ─────────────────────────────────────────────────────────
    if TILING["ativo"]:
        grades  = TILING["grades"]
        overlap = TILING["overlap"]
        log.info("YOLO — tiling %dx%d (overlap=%.0f%%)...",
                 grades, grades, overlap * 100)

        tile_h = int(altura / grades * (1 + overlap))
        tile_w = int(largura / grades * (1 + overlap))

        for row in range(grades):
            for col in range(grades):
                y1_t = int(row * altura / grades)
                x1_t = int(col * largura / grades)
                y2_t = min(y1_t + tile_h, altura)
                x2_t = min(x1_t + tile_w, largura)

                tile = img_analise[y1_t:y2_t, x1_t:x2_t]
                # Redimensiona para imgsz antes de passar ao YOLO
                imgsz = YOLO_PARAMS["imgsz"]
                tile_r = cv2.resize(tile, (imgsz, imgsz))

                # Parâmetros do tile: mesmos do YOLO_PARAMS exceto imgsz fixo
                params_tile = {**YOLO_PARAMS, "imgsz": imgsz}
                res_t = model(tile_r, device=device, **params_tile)

                for r in res_t:
                    for box in r.boxes:
                        conf = float(box.conf[0])
                        sx = tile.shape[1] / imgsz
                        sy = tile.shape[0] / imgsz
                        bx1 = int(float(box.xyxy[0][0]) * sx) + x1_t
                        by1 = int(float(box.xyxy[0][1]) * sy) + y1_t
                        bx2 = int(float(box.xyxy[0][2]) * sx) + x1_t
                        by2 = int(float(box.xyxy[0][3]) * sy) + y1_t
                        deteccoes_brutas.append(
                            (bx1, by1, bx2, by2, conf, f"tile({row},{col})")
                        )

    # ── 3. Filtro geométrico ──────────────────────────────────────────────
    det = _filtrar_deteccoes(deteccoes_brutas, largura, altura)

    if not det:
        log.info("0 pessoa(s) detectada(s) após filtros.")
        return 0, None

    # ── 4. Anotação ───────────────────────────────────────────────────────
    img_anotada = img_original.copy()
    for d in det:
        x1, y1, x2, y2 = d["bbox"]
        cv2.rectangle(img_anotada, (x1, y1), (x2, y2), (0, 0, 255), 3)
        label = f"Pessoa {d['confianca']:.2f}"
        cv2.putText(
            img_anotada, label,
            (x1, max(y1 - 10, 10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2,
        )
        log.info(
            "Pessoa | conf=%.2f area=%d larg=%d alt=%d AR=%.2f origem=%s",
            d["confianca"], d["area"], d["largura"],
            d["altura"], d["aspect_ratio"], d["origem"],
        )

    caminho_anotado = caminho_imagem.with_name(
        caminho_imagem.stem + "_deteccao" + caminho_imagem.suffix
    )
    cv2.imwrite(str(caminho_anotado), img_anotada)

    log.info("%d pessoa(s) detectada(s). Imagem: %s",
             len(det), caminho_anotado.name)
    return len(det), caminho_anotado

"""
core/auth.py — Decorator de autenticação.

Extraído de core.py para que as rotas possam importá-lo
sem depender do core.py original (que acessa sqlite3 diretamente).
"""

from __future__ import annotations

from functools import wraps

from flask import flash, jsonify, redirect, request, session, url_for


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "monitor_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"erro": "não autenticado"}), 401
            flash("Faça login para continuar.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

"""
Configuracao centralizada das speed domes.

As cameras sao cadastradas na tabela `nvrs` (PostgreSQL) e seus presets na
tabela `nvr_presets`. Este modulo expoe a mesma interface publica de antes
(NVRConfig, NVRS, buscar_nvr) para nao exigir mudancas em quem ja importa
daqui (routes/ronda_loop.py, core/ronda_multi_nvr.py, etc.), trocando apenas
a origem dos dados: do CSV/XLSX para o banco.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class NVRConfig:
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
    observacoes: str = ""


def _resolver_segredo(valor: str) -> str:
    """
    Permite usar env:NOME_DA_VARIAVEL no banco para nao deixar senha exposta
    em texto plano na tabela. Se a variavel nao existir, retorna string vazia.
    """
    if valor and valor.startswith("env:"):
        return os.getenv(valor[4:], "")
    return valor


def _nvr_para_config(nvr) -> NVRConfig:
    """Converte uma instancia do model Nvr (SQLAlchemy) em NVRConfig."""
    presets = {preset.numero: preset.nome for preset in nvr.presets}

    return NVRConfig(
        id=nvr.nvr_id,
        site=nvr.site or "",
        nome=nvr.nome,
        ip=nvr.ip,
        usuario=nvr.usuario,
        senha=_resolver_segredo(nvr.senha),
        presets=presets,
        tempo_espera=nvr.tempo_espera,
        timeout=nvr.timeout,
        ativo=nvr.ativo,
    )


def carregar_nvrs(incluir_inativos: bool = False) -> list[NVRConfig]:
    """
    Carrega os NVRs cadastrados no banco PostgreSQL.

    Precisa ser chamada dentro do contexto da aplicacao Flask
    (app.app_context()), pois depende da sessao do SQLAlchemy.
    """
    from models.nvr import Nvr  # import local para evitar import circular

    query = Nvr.query
    if not incluir_inativos:
        query = query.filter_by(ativo=True)

    nvrs_db = query.order_by(Nvr.site, Nvr.nome).all()
    return [_nvr_para_config(nvr) for nvr in nvrs_db]


def buscar_nvr(nvr_id: str) -> NVRConfig | None:
    from models.nvr import Nvr  # import local para evitar import circular

    nvr = Nvr.query.filter_by(nvr_id=nvr_id).first()
    return _nvr_para_config(nvr) if nvr else None


def listar_nvrs(incluir_inativos: bool = False) -> list[NVRConfig]:
    """Alias explicito de carregar_nvrs, para compatibilidade com chamadas
    no estilo nvr_db.listar_nvrs() usadas em outras partes do projeto."""
    return carregar_nvrs(incluir_inativos=incluir_inativos)


# NOTA IMPORTANTE:
# Diferente da versao antiga (CSV/XLSX), NVRS deixou de ser uma lista
# carregada automaticamente na importacao do modulo, pois isso exigiria
# contexto de aplicacao Flask/SQLAlchemy disponivel no momento do import
# (o que falha se este modulo for importado antes do app estar criado).
#
# Em vez de "from core.nvr_config import NVRS", use:
#     from core.nvr_config import carregar_nvrs
#     nvrs = carregar_nvrs()
#
# Se algum arquivo do projeto ainda importar NVRS diretamente, ajuste essa
# importacao para chamar carregar_nvrs() dentro de uma rota ou funcao que
# já esteja rodando dentro do contexto da aplicacao.

"""
core/ronda_loop.py — Motor de Ronda Contínua.

Executa rondas em sequência, uma após a outra, até receber sinal de parada.

Mudanças em relação à versão SQLite:
  - _criar_ronda_pai() → RondaRepository.criar() via session_scope()
  Toda operação de banco usa session_scope() — seguro para threads.

Integração com Flask:
    from core.ronda_loop import iniciar_loop, parar_loop, status_loop
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.ronda_multi_nvr import executar_ronda_multi

# =========================================================
# ESTADO GLOBAL (thread-safe via Lock)
# =========================================================

_lock   = threading.Lock()
_thread: Optional[threading.Thread] = None

_estado = {
    "ativo":           False,
    "parar":           False,
    "ciclo_atual":     0,
    "total_ciclos":    0,
    "iniciado_em":     None,
    "ultimo_ciclo":    None,
    "monitor_nome":    "",
    "monitor_id":      None,
    "turno":           "",
    "nvr_ids":         None,
    "log":             [],
    "ultimo_ronda_id": None,
    "ultimo_pasta":    None,
    "erro":            None,
}

MAX_LOG = 100


def _log(msg: str, nivel: str = "INFO") -> None:
    ts   = datetime.now().strftime("%H:%M:%S")
    linha = f"[{ts}] [{nivel}] {msg}"
    logging.getLogger("ronda_loop").log(
        logging.INFO if nivel == "INFO" else logging.WARNING, msg
    )
    with _lock:
        _estado["log"].append(linha)
        if len(_estado["log"]) > MAX_LOG:
            _estado["log"] = _estado["log"][-MAX_LOG:]


# =========================================================
# BANCO — cria ronda pai via repository
# =========================================================

def _criar_ronda_pai(
    monitor_id: int,
    monitor_nome: str,
    turno: str,
    pasta: str,
) -> Optional[int]:
    """
    Insere ronda pai usando RondaRepository + session_scope().
    Substitui _criar_ronda_pai() com sqlite3 direto.
    Retorna o ID gerado ou None em caso de falha.
    """
    try:
        from repositories.db_session import session_scope
        from repositories.ronda_repository import RondaRepository
        with session_scope() as session:
            ronda = RondaRepository(session=session).criar(
                monitor_id=monitor_id,
                monitor_nome=monitor_nome,
                turno=turno,
                pasta=pasta,
            )
            return ronda.id
    except Exception as e:
        _log(f"Erro ao criar ronda no banco: {e}", "WARN")
        return None


# =========================================================
# WORKER — roda em thread separada
# =========================================================

def _worker(
    monitor_id: int,
    monitor_nome: str,
    turno: str,
    nvr_ids: Optional[list],
) -> None:
    _log(f"=== LOOP DE RONDA INICIADO | Monitor: {monitor_nome} | Turno: {turno} ===")

    with _lock:
        _estado["ativo"]        = True
        _estado["parar"]        = False
        _estado["ciclo_atual"]  = 0
        _estado["total_ciclos"] = 0
        _estado["iniciado_em"]  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _estado["ultimo_ciclo"] = None
        _estado["erro"]         = None

    try:
        while True:
            with _lock:
                deve_parar = _estado["parar"]
            if deve_parar:
                _log("Sinal de parada recebido. Encerrando após ciclo atual.")
                break

            with _lock:
                _estado["ciclo_atual"] += 1
                ciclo = _estado["ciclo_atual"]

            _log(f"--- Iniciando ciclo #{ciclo} ---")

            ts    = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            pasta = str(Path("relatorios") / f"loop_{ts}_ciclo{ciclo:03d}")

            ronda_id = _criar_ronda_pai(monitor_id, monitor_nome, turno, pasta)

            with _lock:
                _estado["ultimo_ronda_id"] = ronda_id
                _estado["ultimo_pasta"]    = pasta

            try:
                executar_ronda_multi(
                    monitor_nome=monitor_nome,
                    turno=turno,
                    pasta=pasta,
                    ronda_id=ronda_id,
                    nvr_ids=nvr_ids,
                )
                with _lock:
                    _estado["total_ciclos"] += 1
                    _estado["ultimo_ciclo"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _log(f"Ciclo #{ciclo} concluído. Total: {_estado['total_ciclos']}")

            except Exception as e:
                _log(f"Erro no ciclo #{ciclo}: {e}", "WARN")
                with _lock:
                    _estado["erro"] = str(e)
                continue

            with _lock:
                deve_parar = _estado["parar"]
            if deve_parar:
                _log("Sinal de parada recebido. Loop encerrado após ciclo concluído.")
                break

    except Exception as e:
        _log(f"Erro crítico no loop: {e}", "WARN")
        with _lock:
            _estado["erro"] = str(e)
    finally:
        with _lock:
            _estado["ativo"]       = False
            _estado["ciclo_atual"] = 0
        _log("=== LOOP DE RONDA ENCERRADO ===")


# =========================================================
# API PÚBLICA
# =========================================================

def iniciar_loop(
    monitor_id: int,
    monitor_nome: str,
    turno: str,
    nvr_ids: Optional[list] = None,
) -> dict:
    """
    Inicia o loop de ronda contínua em background.
    Retorna {"ok": True} ou {"erro": "motivo"}.
    """
    global _thread

    with _lock:
        if _estado["ativo"]:
            return {"erro": "Loop já está em execução."}

        _estado["monitor_id"]   = monitor_id
        _estado["monitor_nome"] = monitor_nome
        _estado["turno"]        = turno
        _estado["nvr_ids"]      = nvr_ids
        _estado["log"]          = []

    _thread = threading.Thread(
        target=_worker,
        args=(monitor_id, monitor_nome, turno, nvr_ids),
        daemon=True,
        name="ronda-loop",
    )
    _thread.start()
    return {"ok": True}


def parar_loop() -> dict:
    """
    Sinaliza parada. A ronda em curso termina normalmente;
    nenhuma nova é iniciada após a conclusão.
    """
    with _lock:
        if not _estado["ativo"]:
            return {"erro": "Loop não está em execução."}
        _estado["parar"] = True

    _log("Parada solicitada. Aguardando fim do ciclo atual...")
    return {"ok": True}


def status_loop() -> dict:
    """Retorna snapshot do estado atual do loop."""
    with _lock:
        return {
            "ativo":           _estado["ativo"],
            "parar":           _estado["parar"],
            "ciclo_atual":     _estado["ciclo_atual"],
            "total_ciclos":    _estado["total_ciclos"],
            "iniciado_em":     _estado["iniciado_em"],
            "ultimo_ciclo":    _estado["ultimo_ciclo"],
            "monitor_nome":    _estado["monitor_nome"],
            "turno":           _estado["turno"],
            "ultimo_ronda_id": _estado["ultimo_ronda_id"],
            "ultimo_pasta":    _estado["ultimo_pasta"],
            "erro":            _estado["erro"],
            "log":             list(_estado["log"][-20:]),
        }

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

load_dotenv()

# =========================================================
# CONFIGURAÇÕES YOLO
# =========================================================

MODELO_YOLO      = caminho_modelo_yolo()
CONFIANCA_MINIMA = 0.30
INPUT_SIZE       = 960
TILES            = 3
OVERLAP          = 0.20
IOU              = 0.45
AREA_MINIMA      = 900
LARGURA_MINIMA   = 14
ALTURA_MINIMA    = 32
ASPECT_RATIO_MIN = 1.6

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
# ANÁLISE YOLO
# =========================================================

def remover_overlays(img):
    h, w = img.shape[:2]
    img[0 : int(h * 0.20), :] = 0
    img[int(h * 0.65) :, int(w * 0.50) :] = 0
    return img


def filtrar_deteccoes_tile(
    deteccoes_brutas: list,
    largura_img: int,
    altura_img: int,
) -> list:
    validas = []
    for x1, y1, x2, y2, conf, origem in deteccoes_brutas:
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        if cy < altura_img * 0.20:
            continue
        if cx > largura_img * 0.50 and cy > altura_img * 0.65:
            continue

        larg = x2 - x1
        alt  = y2 - y1
        area = larg * alt
        ar   = alt / max(larg, 1)

        if area < AREA_MINIMA or larg < LARGURA_MINIMA:
            continue
        if alt < ALTURA_MINIMA or ar < ASPECT_RATIO_MIN:
            continue

        validas.append({
            "bbox":         (x1, y1, x2, y2),
            "confianca":    conf,
            "area":         area,
            "largura":      larg,
            "altura":       alt,
            "aspect_ratio": ar,
            "origem":       origem,
        })
    return validas


def analisar_imagem(
    caminho_imagem: Path,
    log: logging.Logger,
) -> tuple[int, Path | None]:
    model = get_model()
    img_original = cv2.imread(str(caminho_imagem))
    if img_original is None:
        log.error("Não foi possível ler imagem: %s", caminho_imagem)
        return 0, None

    img_analise = remover_overlays(img_original.copy())
    altura, largura = img_analise.shape[:2]
    deteccoes_brutas = []

    # Imagem inteira
    log.info("Inferência — imagem inteira (device=%s)...", DEVICE)
    res = model(
        img_analise,
        classes=[0],
        conf=CONFIANCA_MINIMA,
        imgsz=INPUT_SIZE,
        iou=IOU,
        device=DEVICE,
        half=USAR_FP16,
        verbose=False,
    )
    for r in res:
        for box in r.boxes:
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            deteccoes_brutas.append((x1, y1, x2, y2, conf, "inteira"))

    # Tiling
    log.info("Inferência — tiling %dx%d (overlap=%.0f%%)...", TILES, TILES, OVERLAP * 100)
    tile_h = int(altura / TILES * (1 + OVERLAP))
    tile_w = int(largura / TILES * (1 + OVERLAP))

    for row in range(TILES):
        for col in range(TILES):
            y1_tile = int(row * altura / TILES)
            x1_tile = int(col * largura / TILES)
            y2_tile = min(y1_tile + tile_h, altura)
            x2_tile = min(x1_tile + tile_w, largura)

            tile = img_analise[y1_tile:y2_tile, x1_tile:x2_tile]
            tile_resized = cv2.resize(tile, (INPUT_SIZE, INPUT_SIZE))

            res_tile = model(
                tile_resized,
                classes=[0],
                conf=CONFIANCA_MINIMA,
                imgsz=INPUT_SIZE,
                iou=IOU,
                device=DEVICE,
                half=USAR_FP16,
                verbose=False,
            )
            for r in res_tile:
                for box in r.boxes:
                    conf = float(box.conf[0])
                    bx1 = int(box.xyxy[0][0] * (tile.shape[1] / INPUT_SIZE)) + x1_tile
                    by1 = int(box.xyxy[0][1] * (tile.shape[0] / INPUT_SIZE)) + y1_tile
                    bx2 = int(box.xyxy[0][2] * (tile.shape[1] / INPUT_SIZE)) + x1_tile
                    by2 = int(box.xyxy[0][3] * (tile.shape[0] / INPUT_SIZE)) + y1_tile
                    deteccoes_brutas.append(
                        (bx1, by1, bx2, by2, conf, f"tile({row},{col})")
                    )

    det = filtrar_deteccoes_tile(deteccoes_brutas, largura, altura)

    if not det:
        log.info("0 pessoa(s) detectada(s).")
        return 0, None

    img_anotada = img_original.copy()
    for d in det:
        x1, y1, x2, y2 = d["bbox"]
        cv2.rectangle(img_anotada, (x1, y1), (x2, y2), (0, 0, 255), 3)
        cv2.putText(
            img_anotada,
            f"Pessoa {d['confianca']:.2f}",
            (x1, max(y1 - 10, 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )
        log.info(
            "Pessoa detectada | Confiança: %.2f | Área: %d | "
            "Largura: %d | Altura: %d | AR: %.2f | Origem: %s",
            d["confianca"], d["area"], d["largura"],
            d["altura"], d["aspect_ratio"], d["origem"],
        )

    caminho_anotado = caminho_imagem.with_name(
        caminho_imagem.stem + "_deteccao" + caminho_imagem.suffix
    )
    cv2.imwrite(str(caminho_anotado), img_anotada)
    log.info("%d pessoa(s) detectada(s). Imagem anotada: %s", len(det), caminho_anotado.name)
    return len(det), caminho_anotado


# =========================================================
# RONDA DE UM ÚNICO NVR (roda em thread própria)
# =========================================================

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

        pessoas, imagem_anotada = analisar_imagem(imagem, log)
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

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MODELOS_DIR = BASE_DIR / "modelos_treinados"
MODELO_TREINADO_PADRAO = MODELOS_DIR / "speed_dome_pessoas" / "best.pt"
MODELO_BASE_PADRAO = "yolov8n.pt"


def caminho_modelo_yolo() -> str:
    """
    Prioridade:
    1. Variavel YOLO_MODEL_PATH.
    2. Modelo treinado local em modelos_treinados/speed_dome_pessoas/best.pt.
    3. Modelo base yolov8n.pt.
    """
    modelo_env = os.getenv("YOLO_MODEL_PATH")
    if modelo_env:
        return modelo_env
    if MODELO_TREINADO_PADRAO.exists():
        return str(MODELO_TREINADO_PADRAO)
    return MODELO_BASE_PADRAO
