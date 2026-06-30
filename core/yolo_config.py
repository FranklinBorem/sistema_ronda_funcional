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
