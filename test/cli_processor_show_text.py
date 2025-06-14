#!/usr/bin/env python3
"""Aplicación CLI para procesar un PDF bancario.

- Detecta el banco
- Muestra el texto extraído después de `process_pdf`
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from pdf_processor import PDFProcessor  # noqa: E402



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Procesa un extracto bancario PDF y muestra el texto extraído"
    )
    parser.add_argument("pdf", help="Ruta al archivo PDF a procesar")
    args = parser.parse_args()

    pdf_path = os.path.abspath(args.pdf)
    if not os.path.isfile(pdf_path):
        print(f"❌ Archivo no encontrado: {pdf_path}")
        return

    processor = PDFProcessor()

    # Procesar para obtener transacciones y banco detectado
    result = processor.process_pdf(pdf_path, os.path.basename(pdf_path))
    if not result.get("success"):
        print("⚠️  No se extrajeron transacciones.")
        if "error" in result:
            print("Error:", result["error"])
        return

    bank = result.get("bank_name") or result.get("bank_detected", "Desconocido")
    print(f"\nBanco detectado: {bank}\n")

    # Extraer texto para mostrarlo
    text_content = processor._extract_text_from_pdf(pdf_path)
    print("===== TEXTO EXTRAÍDO =====\n")
    print(text_content or "[Sin texto]")
    print("\n===== FIN DEL TEXTO =====\n")


    print(f"Total de transacciones extraídas: {len(result['transactions'])}")


if __name__ == "__main__":
    main()
