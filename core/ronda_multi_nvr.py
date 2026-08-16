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


def _camera_v2_para_config(camera) -> NVRConfig:
    """
    Converte um models_v2.Camera (PTZ, com presets) para NVRConfig.

    ADAPTAÇÃO ESTRUTURAL (não é um simples rename de _nvr_para_config):
    no schema antigo, "Nvr" representava UMA câmera PTZ individual
    (com seu próprio IP/canal). No schema novo, `Nvr` é o grupo/site
    (pode ter várias câmeras), e cada `Camera` com capacidade PTZ é
    quem tem canal + presets — logo, a unidade de trabalho da ronda
    passa a ser uma Camera, não um Nvr inteiro. Ver
    docs/database/modelo-banco.md e a conversa sobre modo_conexao.

    Resolve IP/usuário/credencial da própria câmera quando
    modo_conexao='ip_direto', ou do NVR físico pai quando
    modo_conexao='via_nvr'.

    GAPS CONHECIDOS (sem equivalente no schema novo ainda, usando
    valor padrão até virarem campos reais — não bloqueiam a ronda,
    mas afinamento fino por câmera fica indisponível por ora):
    - tempo_espera / timeout: eram configuráveis por NVR no schema
      antigo; usam os defaults do próprio dataclass NVRConfig até
      isso ser modelado como campo real, se necessário.
    - ativo: models_v2.Camera não tem campo de status próprio ainda
      (herda do status do Nvr pai); sempre True aqui.
    """
    nvr = camera.nvr
    if camera.modo_conexao == "ip_direto":
        ip = camera.endereco_ip
        usuario = camera.usuario_acesso or ""
        senha = camera.credencial_ref or ""
        snapshot_channel = "101"
    else:  # via_nvr
        ip = nvr.endereco_ip
        usuario = nvr.usuario_acesso or ""
        senha = nvr.credencial_ref or ""
        snapshot_channel = f"{camera.canal}01"

    return NVRConfig(
        id=str(camera.id),
        nome=camera.nome or f"Câmera {camera.id}",
        ip=ip or "",
        usuario=usuario,
        senha=senha,
        ptz_channel=camera.canal or 1,
        snapshot_channel=snapshot_channel,
        presets={p.numero: (p.descricao or f"Preset {p.numero}") for p in camera.presets},
        tempo_espera=NVRConfig.__dataclass_fields__["tempo_espera"].default,
        timeout=NVRConfig.__dataclass_fields__["timeout"].default,
        site=nvr.unidade.nome if nvr.unidade else "",
        ativo=True,
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
# PERSISTÊNCIA — SCHEMA NOVO (models_v2), Fase C da religação
# =========================================================
# As três funções abaixo são os equivalentes v2 das três acima.
# Coexistem com as antigas (não as substituem) até a orquestração de
# executar_ronda_multi() ser efetivamente religada para usar Camera em
# vez de Nvr como unidade de trabalho — o que exige validação contra
# hardware real (NVR/câmera físicos), indisponível neste ambiente de
# desenvolvimento. Ver core/camera_config_v2.py para a discussão
# completa dessa adaptação estrutural.

def _salvar_resultado_nvr_v2(
    ronda_pai_id: int | None,
    nvr_id: int,
    status: str,
    imagens_ref: dict | None = None,
) -> None:
    """Equivalente v2 de _salvar_ronda_nvr — usa RondaRepository (repositories_v2)."""
    try:
        from repositories_v2.db_session import session_scope
        from repositories_v2.ronda_repository import RondaRepository
        with session_scope() as session:
            RondaRepository(session=session).registrar_resultado_nvr(
                ronda_id=ronda_pai_id,
                nvr_id=nvr_id,
                status=status,
                imagens_ref=imagens_ref,
            )
    except Exception as e:
        print(f"[AVISO DB v2] salvar_resultado_nvr: {e}")


def _atualizar_ronda_pai_v2(ronda_id: int | None, status: str) -> None:
    """Equivalente v2 de _atualizar_ronda_pai — usa RondaRepository (repositories_v2)."""
    if not ronda_id:
        return
    try:
        from repositories_v2.db_session import session_scope
        from repositories_v2.ronda_repository import RondaRepository
        with session_scope() as session:
            RondaRepository(session=session).finalizar(ronda_id=ronda_id, status=status)
    except Exception as e:
        print(f"[AVISO DB v2] atualizar_ronda_pai: {e}")


def _registrar_ocorrencia_deteccao_v2(
    ronda_id: int | None,
    nvr_id: int,
    pessoas: int,
    local_preset: str,
    imagem_path: str | None,
    detectado_em: datetime,
) -> None:
    """Equivalente v2 de _registrar_alerta — cria uma Ocorrencia (repositories_v2)."""
    try:
        from repositories_v2.db_session import session_scope
        from repositories_v2.ronda_repository import RondaRepository
        with session_scope() as session:
            RondaRepository(session=session).registrar_ocorrencia_deteccao(
                nvr_id=nvr_id,
                pessoas=pessoas,
                local_preset=local_preset,
                imagem_path=imagem_path,
                detectado_em=detectado_em,
                ronda_id=ronda_id,
            )
    except Exception as e:
        print(f"[AVISO DB v2] registrar_ocorrencia_deteccao: {e}")


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
# ORQUESTRAÇÃO — SCHEMA NOVO (models_v2), Fase C da religação
# =========================================================
# NÃO VALIDADO CONTRA HARDWARE REAL — sem NVR/câmera físico disponível
# neste ambiente de desenvolvimento. A lógica de PTZ/captura/análise
# em si (mover_ptz, capturar_snapshot, analisar_imagem) é IDÊNTICA à
# usada pelo caminho antigo já em produção — só a montagem da lista de
# trabalho e a persistência de resultado mudam aqui. Testar com um NVR
# real antes de usar em operação é o próximo passo, fora do alcance
# deste ambiente.

def executar_ronda_camera_v2(
    cfg: NVRConfig,
    nvr_id_real: int,
    pasta_raiz: Path,
    ronda_pai_id: int | None,
    log_global: logging.Logger,
) -> dict:
    """
    Equivalente v2 de executar_ronda_nvr — mesma lógica de PTZ/captura/
    análise (inalterada), trocando apenas a persistência para
    repositories_v2. `nvr_id_real` é o ID inteiro do Nvr (grupo/site)
    dono da câmera — necessário porque cfg.id agora é o ID da própria
    Camera (usado para nomear a pasta de evidências), não o do Nvr.
    """
    t_inicio   = time.time()
    pasta_nvr  = pasta_raiz / cfg.id
    pasta_imgs = pasta_nvr / "imagens"
    pasta_imgs.mkdir(parents=True, exist_ok=True)

    log = criar_logger(cfg.id, pasta_nvr)
    log.info("=== INICIANDO RONDA v2 | Câmera: %s | IP: %s ===", cfg.nome, cfg.ip)

    sessao = criar_sessao(cfg)

    if not testar_autenticacao(sessao, cfg, log):
        log.error("Falha na autenticação. Abortando câmera.")
        _salvar_resultado_nvr_v2(ronda_pai_id, nvr_id_real, "erro")
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

                _registrar_ocorrencia_deteccao_v2(
                    ronda_id=ronda_pai_id,
                    nvr_id=nvr_id_real,
                    pessoas=pessoas,
                    local_preset=nome_local,
                    imagem_path=imagem_path_banco,
                    detectado_em=datetime.now(),
                )
                log.info("Ocorrência registrada: %s (%d pessoa(s))", nome_local, pessoas)
            except Exception as e:
                log.warning("Não foi possível registrar ocorrência: %s", e)

        linhas.append({
            "horario":    datetime.now().strftime("%H:%M:%S"),
            "nome_local": nome_local,
            "status":     "INVASÃO DETECTADA" if pessoas > 0 else "NORMAL",
            "classe_css": "alerta" if pessoas > 0 else "normal",
            "pessoas":    pessoas,
        })

    duracao      = int(time.time() - t_inicio)
    status_final = "com_alertas" if invasoes > 0 else "finalizada"
    _salvar_resultado_nvr_v2(ronda_pai_id, nvr_id_real, status_final)

    log.info("=== RONDA CÂMERA v2 FINALIZADA | Invasões: %d | Duração: %ds ===",
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


def executar_ronda_multi_v2(
    unidade_id: int,
    monitor_nome: str = "Não informado",
    turno: str = "Não informado",
    pasta: str | None = None,
    ronda_id: int | None = None,
    max_workers: int | None = None,
) -> None:
    """
    Equivalente v2 de executar_ronda_multi — busca câmeras PTZ com
    preset de uma Unidade (em vez de todos os "Nvr" do schema antigo),
    e delega a mesma lógica de PTZ/captura/análise já usada em
    produção. Ver docstring da seção acima sobre a falta de validação
    contra hardware real neste ambiente.
    """
    from repositories_v2.db_session import session_scope
    from repositories_v2.nvr_repository import NvrRepository

    with session_scope() as session:
        cameras_db = NvrRepository(session=session).listar_cameras_ptz_por_unidade(unidade_id)
        # (camera_id_str, nvr_id_real, NVRConfig) — resolvido dentro da sessão,
        # antes dela fechar, pois _camera_v2_para_config acessa relationships
        # (camera.nvr, camera.presets) que exigem sessão viva.
        trabalho = [
            (nvr_id := cam.nvr_id, _camera_v2_para_config(cam))
            for cam in cameras_db
        ]

    if not trabalho:
        print("❌ Nenhuma câmera PTZ com preset encontrada para esta unidade.")
        return

    if max_workers is None:
        max_workers = len(trabalho)

    timestamp  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pasta_raiz = Path(pasta) if pasta else Path("relatorios") / f"multi_{timestamp}"
    pasta_raiz.mkdir(parents=True, exist_ok=True)

    log_global = criar_logger("MULTI-V2", pasta_raiz)
    log_global.info(
        "=== RONDA MULTI v2 | Monitor: %s | Turno: %s | Câmeras: %d ===",
        monitor_nome, turno, len(trabalho),
    )

    resultados_ordenados = []
    futuros = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for nvr_id_real, cfg in trabalho:
            f = executor.submit(
                executar_ronda_camera_v2, cfg, nvr_id_real, pasta_raiz, ronda_id, log_global
            )
            futuros[f] = cfg.id

        for futuro in as_completed(futuros):
            cam_id_key = futuros[futuro]
            try:
                resultado = futuro.result()
                resultados_ordenados.append(resultado)
                log_global.info(
                    "✅ Câmera %s concluída | Invasões: %d",
                    resultado["nome"], resultado["invasoes"],
                )
            except Exception as e:
                log_global.error("❌ Câmera %s lançou exceção: %s", cam_id_key, e)
                resultados_ordenados.append({
                    "id": cam_id_key, "nome": cam_id_key, "ip": "?",
                    "erro": str(e), "linhas": [], "invasoes": 0, "duracao_s": 0,
                })

    ordem = {cfg.id: i for i, (_, cfg) in enumerate(trabalho)}
    resultados_ordenados.sort(key=lambda r: ordem.get(r["id"], 999))

    arquivo_html = gerar_relatorio_multi(
        pasta_raiz, resultados_ordenados, monitor_nome, turno
    )

    total_invasoes = sum(r["invasoes"] for r in resultados_ordenados)
    cameras_ok = [r for r in resultados_ordenados if not r.get("erro")]
    status_pai = ("com_alertas" if total_invasoes > 0 else "finalizada") if cameras_ok else "erro"
    _atualizar_ronda_pai_v2(ronda_id, status_pai)

    log_global.info("=== MULTI-RONDA v2 FINALIZADA ===")
    log_global.info("Invasões totais: %d", total_invasoes)
    log_global.info("Relatório: %s", arquivo_html)
    print(f"\n✅ Ronda finalizada. Relatório: {arquivo_html}")

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
