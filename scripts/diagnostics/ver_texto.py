import argparse
from pathlib import Path

import pdfplumber


def main() -> None:
    parser = argparse.ArgumentParser(description="Muestra el texto extraído de un PDF página por página.")
    parser.add_argument(
        "pdf",
        nargs="?",
        default=str(Path("local_samples") / "chase" / "BANCO CH 2024 1.pdf"),
        help="Ruta al PDF",
    )
    args = parser.parse_args()

    with pdfplumber.open(args.pdf) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            print(f"\n--- Página {i} ---\n")
            text = page.extract_text()
            if text:
                print(text)
            else:
                print("[Sin texto extraído]")


if __name__ == "__main__":
    main()
