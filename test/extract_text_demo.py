#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_text_demo.py

• Modo normal:
      python extract_text_demo.py archivo.pdf
• Modo raw (muestra texto por columnas con la lógica del parser):
      python extract_text_demo.py archivo.pdf --raw
"""
import sys
import os
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from pdf_processor import PDFProcessor  # noqa: E402

CAMPOS = [
    "date", "description", "amount", "balance",
    "account", "bank", "currency", "transaction_type",
]

# --------------------------------------------------------------------------- #
# MODO RAW: usa los parámetros del parser real                                #
# --------------------------------------------------------------------------- #
def show_raw_text_by_column(pdf_path: str) -> None:
    import pdfplumber

    processor = PDFProcessor()

    # 1) Extraer texto una sola vez
    text_content = processor._extract_text_from_pdf(pdf_path)
    # 2) Detectar banco con el método interno
    bank_id = processor._detect_bank(text_content)
    parser   = processor.parser_factory.get_parser(bank_id)
    ParserCl = parser.__class__

    # 3) Leer parámetros de corte definidos en el parser
    split_ratio = getattr(ParserCl, "SPLIT_RATIO", 0.5)
    margin      = getattr(ParserCl, "MARGIN", 0)
    char_margin = getattr(ParserCl, "CHAR_MARGIN", 2)

    print(f"\n===== RAW • parser={ParserCl.__name__} "
          f"ratio={split_ratio} margin={margin} char_margin={char_margin} =====")

    with pdfplumber.open(pdf_path) as pdf:
        for num, page in enumerate(pdf.pages, 1):
            split_x = page.width * split_ratio
            left_bbox  = (0, 0, split_x + margin, page.height)
            right_bbox = (split_x - margin, 0, page.width, page.height)

            left  = page.crop(left_bbox ).extract_text(char_margin=char_margin)
            right = page.crop(right_bbox).extract_text(char_margin=char_margin)

            print(f"\n--- PÁGINA {num} • COLUMNA IZQUIERDA ---")
            print(left or "[VACÍO]")
            print(f"\n--- PÁGINA {num} • COLUMNA DERECHA ---")
            print(right or "[VACÍO]")

    print("\n===== FIN RAW =====")
    sys.exit(0)

# --------------------------------------------------------------------------- #
# MODO NORMAL                                                                 #
# --------------------------------------------------------------------------- #
def process_pdf(pdf_path: str) -> None:
    processor = PDFProcessor()
    result = processor.process_pdf(pdf_path, os.path.basename(pdf_path))

    if not result.get("success"):
        print("⚠️  No se extrajo ninguna transacción.")
        if "error" in result:
            print("Error:", result["error"])
        return

    transacciones = result["transactions"]

    header = " | ".join(f"{c.upper():<20}" for c in CAMPOS)
    print(header)
    print("-" * len(header))

    for t in transacciones:
        fila = " | ".join(f"{str(t.get(c, '')):<20}" for c in CAMPOS)
        print(fila)

    print(f"\nTotal de transacciones: {len(transacciones)}")

# --------------------------------------------------------------------------- #
# MAIN                                                                        #
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="Demo de extracción PDF")
    parser.add_argument("pdf", help="Ruta al archivo PDF")
    parser.add_argument("-r", "--raw", action="store_true",
                        help="Mostrar texto crudo por columnas y salir")
    args = parser.parse_args()

    pdf_path = os.path.abspath(args.pdf)
    if not os.path.isfile(pdf_path):
        print("❌ Archivo no encontrado.")
        sys.exit(1)

    if args.raw:
        show_raw_text_by_column(pdf_path)
    else:
        process_pdf(pdf_path)

if __name__ == "__main__":
    main()
