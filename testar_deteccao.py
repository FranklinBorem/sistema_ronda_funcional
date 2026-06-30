# -*- coding: utf-8 -*-
"""
Vigilante IA - Teste de Deteccao
Reproduz exatamente a logica de ronda_multi_nvr.py + analisar_imagem.py
"""

import argparse
import logging
import os
import sys
import time
import threading
from pathlib import Path

import cv2
import numpy as np

# ─── Parametros identicos ao ronda_multi_nvr.py ───────────────────────────────
CONFIANCA_MINIMA = 0.30
INPUT_SIZE       = 960
TILES            = 3
OVERLAP          = 0.20
IOU              = 0.45
AREA_MINIMA      = 900
LARGURA_MINIMA   = 14
ALTURA_MINIMA    = 32
ASPECT_RATIO_MIN = 1.6

# Remocao de overlays da camera (frações da imagem)
REMOVER_TOPO_FRAC    = 0.04   # 4% do topo zerado
REMOVER_RODAPE_FRAC  = 0.93   # abaixo de 93% da altura
REMOVER_RODAPE_X_FRAC = 0.60  # apenas na metade direita

EXTENSOES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# ─── Cores terminal ────────────────────────────────────────────────────────────
G = "\033[92m"   # verde
A = "\033[93m"   # amarelo
V = "\033[91m"   # vermelho
C = "\033[96m"   # ciano
N = "\033[1m"    # negrito
R = "\033[0m"    # reset

# ─── Selecao de device ─────────────────────────────────────────────────────────
def detectar_device() -> str:
    env = os.getenv("YOLO_DEVICE", "").strip()
    if env:
        return env
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:0"
    except ImportError:
        pass
    return "cpu"

# ─── Remocao de overlays ───────────────────────────────────────────────────────
def remover_overlays(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    img[: int(h * REMOVER_TOPO_FRAC), :] = 0
    img[int(h * REMOVER_RODAPE_FRAC):, int(w * REMOVER_RODAPE_X_FRAC):] = 0
    return img

# ─── Filtro geometrico ─────────────────────────────────────────────────────────
def filtrar_deteccoes(brutas: list, largura: int, altura: int) -> list:
    validas = []
    for (x1, y1, x2, y2, conf, origem) in brutas:
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        # Remove overlays da camera
        if cy < altura * REMOVER_TOPO_FRAC:
            continue
        if cx > largura * REMOVER_RODAPE_X_FRAC and cy > altura * REMOVER_RODAPE_FRAC:
            continue

        larg = x2 - x1
        alt  = y2 - y1
        area = larg * alt
        ar   = alt / max(larg, 1)

        motivo = None
        if area < AREA_MINIMA:
            motivo = f"area={area:.0f} < {AREA_MINIMA}"
        elif larg < LARGURA_MINIMA:
            motivo = f"largura={larg:.0f} < {LARGURA_MINIMA}"
        elif alt < ALTURA_MINIMA:
            motivo = f"altura={alt:.0f} < {ALTURA_MINIMA}"
        elif ar < ASPECT_RATIO_MIN:
            motivo = f"AR={ar:.2f} < {ASPECT_RATIO_MIN}"

        validas.append({
            "bbox":    (x1, y1, x2, y2),
            "conf":    conf,
            "area":    area,
            "largura": larg,
            "altura":  alt,
            "ar":      ar,
            "origem":  origem,
            "filtrada": motivo,
        })
    return validas

# ─── Analise de uma imagem ─────────────────────────────────────────────────────
def analisar_imagem(img_path: Path, model, device: str) -> dict:
    print(f"\n  {N}Imagem: {img_path.name}{R}")

    img_orig = cv2.imread(str(img_path))
    if img_orig is None:
        print(f"    {V}[ERRO] Nao foi possivel ler a imagem{R}")
        return {"arquivo": img_path.name, "detectado": False, "erro": True}

    img = remover_overlays(img_orig.copy())
    altura, largura = img.shape[:2]
    brutas = []

    # ── Inferencia imagem inteira ──────────────────────────────────────────────
    t0 = time.perf_counter()
    res = model(img, device=device, conf=CONFIANCA_MINIMA,
                imgsz=INPUT_SIZE, iou=IOU, classes=[0], verbose=False)
    ms = (time.perf_counter() - t0) * 1000
    n_inteira = 0
    for r in res:
        for box in r.boxes:
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            brutas.append((x1, y1, x2, y2, conf, "inteira"))
            n_inteira += 1
    print(f"    [Imagem inteira] {n_inteira} det(s) brutas  ({ms:.0f} ms)")

    # ── Tiling {TILES}x{TILES} ────────────────────────────────────────────────
    tile_h = int(altura / TILES * (1 + OVERLAP))
    tile_w = int(largura / TILES * (1 + OVERLAP))
    n_tiles = 0
    t0 = time.perf_counter()
    for row in range(TILES):
        for col in range(TILES):
            y1_t = int(row * altura / TILES)
            x1_t = int(col * largura / TILES)
            y2_t = min(y1_t + tile_h, altura)
            x2_t = min(x1_t + tile_w, largura)
            tile = img[y1_t:y2_t, x1_t:x2_t]
            tile_r = cv2.resize(tile, (INPUT_SIZE, INPUT_SIZE))
            res_t = model(tile_r, device=device, conf=CONFIANCA_MINIMA,
                          imgsz=INPUT_SIZE, iou=IOU, classes=[0], verbose=False)
            for r in res_t:
                for box in r.boxes:
                    conf = float(box.conf[0])
                    sx = tile.shape[1] / INPUT_SIZE
                    sy = tile.shape[0] / INPUT_SIZE
                    bx1 = int(float(box.xyxy[0][0]) * sx) + x1_t
                    by1 = int(float(box.xyxy[0][1]) * sy) + y1_t
                    bx2 = int(float(box.xyxy[0][2]) * sx) + x1_t
                    by2 = int(float(box.xyxy[0][3]) * sy) + y1_t
                    brutas.append((bx1, by1, bx2, by2, conf, f"tile({row},{col})"))
                    n_tiles += 1
    ms_t = (time.perf_counter() - t0) * 1000
    print(f"    [Tiling {TILES}x{TILES} overlap={OVERLAP:.0%}] {n_tiles} det(s) brutas  ({ms_t:.0f} ms)")

    # ── Filtro geometrico ──────────────────────────────────────────────────────
    dets = filtrar_deteccoes(brutas, largura, altura)
    validas   = [d for d in dets if d["filtrada"] is None]
    filtradas = [d for d in dets if d["filtrada"] is not None]

    for d in validas:
        x1,y1,x2,y2 = d["bbox"]
        print(f"    {G}PESSOA conf={d['conf']:.2%} area={d['area']:.0f} "
              f"larg={d['largura']:.0f} alt={d['altura']:.0f} "
              f"AR={d['ar']:.2f} origem={d['origem']}{R}")

    for d in filtradas:
        x1,y1,x2,y2 = d["bbox"]
        print(f"    {A}FILTRADA conf={d['conf']:.2%} motivo={d['filtrada']} "
              f"origem={d['origem']}{R}")

    detectado = len(validas) > 0

    if not detectado and not dets:
        print(f"    {V}Nenhuma deteccao em nenhum passe{R}")
    elif not detectado:
        print(f"    {V}Detectado mas filtrado — NAO teria disparado alerta{R}")
    else:
        # Salva imagem anotada ao lado da original
        img_anot = img_orig.copy()
        for d in validas:
            x1,y1,x2,y2 = d["bbox"]
            cv2.rectangle(img_anot, (x1,y1), (x2,y2), (0,0,255), 3)
            cv2.putText(img_anot, f"Pessoa {d['conf']:.2f}",
                        (x1, max(y1-10, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
        out = img_path.with_name(img_path.stem + "_deteccao" + img_path.suffix)
        cv2.imwrite(str(out), img_anot)
        print(f"    {G}Imagem anotada salva: {out.name}{R}")

    return {
        "arquivo":   img_path.name,
        "detectado": detectado,
        "n_validas": len(validas),
        "n_filtradas": len(filtradas),
        "n_brutas":  len(brutas),
        "erro":      False,
    }

# ─── Resumo final ──────────────────────────────────────────────────────────────
def resumo(resultados: list):
    total      = len(resultados)
    detectados = sum(1 for r in resultados if r["detectado"])
    nao_det    = total - detectados
    so_filtrou = sum(1 for r in resultados if not r["detectado"] and r.get("n_filtradas",0) > 0)

    print(f"""
{C}{N}
========================================================
  RESUMO FINAL
========================================================{R}
  Total de imagens testadas    : {total}
  {G}Teria DISPARADO alerta       : {detectados}{R}
  {V}NAO teria disparado          : {nao_det}{R}
  {A}  (detectado mas filtrado)   : {so_filtrou}{R}
""")
    if nao_det > 0:
        print(f"  {A}Imagens NAO detectadas:{R}")
        for r in resultados:
            if not r["detectado"] and not r.get("erro"):
                tag = " (filtrado geometricamente)" if r.get("n_filtradas",0) > 0 else ""
                print(f"    - {r['arquivo']}{tag}")
    print()

# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"""
{C}{N}
+----------------------------------------------------------+
|       VIGILANTE IA - TESTE DE DETECCAO DE INVASAO       |
|   Parametros identicos ao ronda_multi_nvr.py            |
+----------------------------------------------------------+{R}
  conf={CONFIANCA_MINIMA}  imgsz={INPUT_SIZE}  iou={IOU}
  tiling={TILES}x{TILES}  overlap={OVERLAP:.0%}
  area_min={AREA_MINIMA}  larg_min={LARGURA_MINIMA}  alt_min={ALTURA_MINIMA}  AR_min={ASPECT_RATIO_MIN}
""")

    parser = argparse.ArgumentParser()
    parser.add_argument("--pasta",
        default="C:/Users/seguranca/Documents/Franklin/teste_nova_crixas")
    parser.add_argument("--modelo", default=None,
        help="Caminho para best.pt (padrao: deteccao automatica)")
    args = parser.parse_args()

    # Modelo
    modelo_path = args.modelo
    if modelo_path is None:
        # Mesma logica de caminho_modelo_yolo()
        treinado = Path("core/modelos_treinados/speed_dome_pessoas/best.pt")
        if treinado.exists():
            modelo_path = str(treinado)
        else:
            modelo_path = "yolov8n.pt"
    print(f"  Modelo  : {modelo_path}")

    device = detectar_device()
    print(f"  Device  : {device}")

    try:
        from ultralytics import YOLO
    except ImportError:
        print(f"{V}[ERRO] ultralytics nao instalado. Execute: pip install ultralytics{R}")
        sys.exit(1)

    print(f"  Carregando modelo...")
    model = YOLO(modelo_path)

    # Imagens
    pasta = Path(args.pasta)
    if not pasta.exists():
        print(f"{V}[ERRO] Pasta nao encontrada: {pasta}{R}")
        sys.exit(1)

    imagens = sorted([f for f in pasta.iterdir() if f.suffix.lower() in EXTENSOES])
    if not imagens:
        print(f"{V}[ERRO] Nenhuma imagem encontrada em: {pasta}{R}")
        sys.exit(1)

    print(f"  Pasta   : {pasta}")
    print(f"  Imagens : {len(imagens)}")

    resultados = []
    for img_path in imagens:
        r = analisar_imagem(img_path, model, device)
        resultados.append(r)

    resumo(resultados)

if __name__ == "__main__":
    main()
