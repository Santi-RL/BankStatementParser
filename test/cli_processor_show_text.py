#!/usr/bin/env python3
"""CLI de diagnóstico para extractos bancarios (ubicado en test/).

Muestra:
  • Banco detectado
  • Texto relevante para depurar
      – Para Banco Roela → flujo ya “alineado” (post-split columnas)
      – Para otros → texto crudo extraído
  • Conteo total de transacciones
  • Vista previa opcional (primeras N transacciones)
  • Debug log opcional
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict

# ─────────────── Configurar ruta raíz del proyecto ───────────────
SCRIPT_DIR = Path(__file__).resolve().parent          # …/test
PROJECT_ROOT = SCRIPT_DIR.parent                      # …/
sys.path.insert(0, str(PROJECT_ROOT))

from pdf_processor import PDFProcessor  # noqa: E402


def reconstruir_texto_desde_transacciones(
    transactions: List[Dict[str, str | float]]
) -> str:
    """Convierte la lista de transacciones en un flujo de texto tabulado.

    Ejemplo de línea resultante:
        03/05/2025\tCOMPRA VISA SUPERMERCADO\t-12 345,67
    """
    filas = []
    for tx in transactions:
        fecha = tx.get("date", "")
        desc = tx.get("description", "")
        monto = tx.get("amount", "")
        filas.append(f"{fecha}\t{desc}\t{monto}")
    return "\n".join(filas)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Procesa un extracto PDF y muestra texto útil para depurar."
    )
    parser.add_argument("pdf", help="Ruta al archivo PDF a procesar")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Muestra el log detallado de depuración",
    )
    parser.add_argument(
        "-p",
        "--preview",
        type=int,
        default=0,
        metavar="N",
        help="Imprime las primeras N transacciones parseadas",
    )
    args = parser.parse_args()

    pdf_path = os.path.abspath(args.pdf)
    if not os.path.isfile(pdf_path):
        print(f"❌ Archivo no encontrado: {pdf_path}")
        return

    processor = PDFProcessor()

    # Procesar PDF completo (detección de banco + parseo)
    result = processor.process_pdf(
        pdf_path, os.path.basename(pdf_path), debug=args.debug
    )

    if not result.get("success"):
        print("⚠️  No se extrajeron transacciones.")
        if "error" in result:
            print("Error:", result["error"])
        if args.debug and "debug_log" in result:
            print("\n===== DEBUG LOG =====")
            for line in result["debug_log"]:
                print(line)
        return

    bank_id = result.get("bank_detected") or result.get("bank_name")
    bank_human = result.get("bank_name", bank_id)
    print(f"\nBanco detectado: {bank_human}\n")

    # ───── Obtener texto según banco ─────
    if bank_id == "roela_ar":
        # Texto alineado reconstruido desde transacciones
        text_content = reconstruir_texto_desde_transacciones(result["transactions"])
        print("===== TEXTO RECONSTRUIDO (post-split columnas) =====\n")
    else:
        # Texto crudo extraído directamente del PDF
        text_content = processor._extract_text_from_pdf(pdf_path)
        print("===== TEXTO EXTRAÍDO =====\n")

    print(text_content or "[Sin texto]")
    print("\n===== FIN DEL TEXTO =====\n")

    # ───── Resumen de transacciones ─────
    transactions = result["transactions"]
    print(f"Total de transacciones extraídas: {len(transactions)}")

    if args.preview > 0:
        print(f"\n===== PRIMERAS {args.preview} TRANSACCIONES =====")
        for tx in transactions[: args.preview]:
            print(tx)
        print("===== FIN DE LA PREVISUALIZACIÓN =====\n")

    # ───── Debug log opcional ─────
    if args.debug and "debug_log" in result:
        print("===== DEBUG LOG =====")
        for line in result["debug_log"]:
            print(line)
        print("===== FIN DEBUG LOG =====")


if __name__ == "__main__":
    main()
