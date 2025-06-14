#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_column_dump.py
Muestra, por página, el texto de la columna izquierda y el de la columna
derecha, usando un punto de corte al 55 % del ancho de cada página.

Uso:
    python pdf_column_dump.py archivo.pdf
"""

import sys
import os
import pdfplumber

# --------- parámetros de extracción ----------------------------------------
SPLIT_RATIO = 0.50   # % del ancho para la columna izquierda
MARGIN      = 3      # margen de seguridad (+izq, –der), en puntos PDF
CHAR_MARGIN = 4      # agrupa caracteres separados por ≤4 pt

# ---------------------------------------------------------------------------
def dump_columns(pdf_path: str) -> None:
    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages, 1):
            split_x = page.width * SPLIT_RATIO

            left_bbox  = (0,             0, split_x + MARGIN, page.height)
            right_bbox = (split_x - MARGIN, 0, page.width,    page.height)

            left_text  = page.crop(left_bbox).extract_text(char_margin=CHAR_MARGIN)  or "[VACÍO]"
            right_text = page.crop(right_bbox).extract_text(char_margin=CHAR_MARGIN) or "[VACÍO]"

            print(f"\n=== PÁGINA {idx} • COLUMNA IZQUIERDA ===")
            print(left_text)

            print(f"\n=== PÁGINA {idx} • COLUMNA DERECHA ===")
            print(right_text)
            print("=" * 60)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pdf_column_dump.py <archivo.pdf>")
        sys.exit(1)

    pdf_file = sys.argv[1]
    if not os.path.isfile(pdf_file):
        print("❌ No se encontró:", pdf_file)
        sys.exit(1)

    dump_columns(pdf_file)
