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
    half = device.startswith("cuda")

    # ── 1. Inferência na imagem inteira ──────────────────────────────────
    log.info("YOLO — imagem inteira (imgsz=%d, conf=%.2f)...",
             YOLO_PARAMS["imgsz"], YOLO_PARAMS["conf"])

    res = model(
        img_analise,
        device=device,
        half=half,
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
                res_t = model(tile_r, device=device, half=half, **params_tile)

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
