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


# =========================================================
# PARÂMETROS DE INFERÊNCIA YOLO
# Extraídos do que já rodava hardcoded em core/ronda_multi_nvr.py.
# Fonte única de verdade — ajuste aqui, não em analisar_imagem.py.
# =========================================================

YOLO_PARAMS = {
    "classes": [0],       # 0 = person no COCO
    "conf":    0.30,
    "imgsz":   960,
    "iou":     0.45,
    "verbose": False,
}

TILING = {
    "ativo":   True,
    "grades":  3,      # grade 3x3
    "overlap": 0.20,
}

FILTRO = {
    "remover_topo_frac":     0.20,
    "remover_rodape_frac":   0.65,
    "remover_rodape_x_frac": 0.50,
    "area_minima":       900,
    "largura_minima":    14,
    "altura_minima":     32,
    "aspect_ratio_min":  1.6,
}