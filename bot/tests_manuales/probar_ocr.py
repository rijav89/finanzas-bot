"""Corré esto a mano con imágenes reales antes de dar por buena la extracción.

Uso: python tests_manuales/probar_ocr.py ruta/a/la/imagen.jpg
"""
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ocr import procesar_voucher

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python probar_ocr.py ruta/a/la/imagen.jpg")
        raise SystemExit(1)

    movimientos = procesar_voucher(sys.argv[1])
    print(f"{len(movimientos)} movimiento(s) leído(s):\n")
    for m in movimientos:
        print(json.dumps(m, indent=2, ensure_ascii=False))
