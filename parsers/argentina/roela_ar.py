from __future__ import annotations

"""
roela_ar.py – Parser para extractos del Banco Roela (Argentina)
=================================================================
Versión v21 (Jul 2025)
-----------------------------------------------------------------
* **Soluciona el error de bounding box**: los recortes de columnas ahora se
  hacen directamente sobre la página usando coordenadas absolutas, evitando
  el uso anidado de `within_bbox`.
* Mantiene el recorte vertical fijo (`HEADER_HEIGHT`/`FOOTER_HEIGHT`).
"""
import re
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any

try:
    import pdfplumber
except Exception:  # pragma: no cover – optional dependency
    pdfplumber = None

from .base import ArgentinianBankParser
from utils import clean_text, parse_date

# ───────────────────── Recorte vertical fijo ──────────────────────
HEADER_HEIGHT: float = 260   # puntos desde el bottom‑left hacia arriba
FOOTER_HEIGHT: float = 30    # puntos desde el bottom‑left hacia abajo
SPLIT_RATIO: float = 0.515   # 51,5 % columna izquierda
MARGIN_PT: float = 4         # margen entre columnas

# ───────────────────── Expresiones regulares ──────────────────────
AMOUNT_RE = re.compile(r"-?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}")
CODE_LINE_RE = re.compile(r"^[A-Z0-9]{1,6}\s+[0-9]{1,15}\b", re.ASCII)

_DEBIT_HINTS = (
    "IMPUESTO",
    "COM.",
    "IVA",
    "DEBITO",
    "DÉBITO",
)

# ───────────────────── Utilidades ──────────────────────

def _importe_roela(amount_str: str) -> Decimal:
    s = amount_str.replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
    if "," in s and "." in s:
        if s.find(",") < s.find("."):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")

def _es_debito(description: str) -> bool:
    return any(token in description.upper() for token in _DEBIT_HINTS)

# ───────────────────── Clase principal ──────────────────────
class RoelaParser(ArgentinianBankParser):
    bank_id = "roela_ar"
    aliases = ["roela"]

    def parse_transactions(self, text: str, filename: str | None = None, **_) -> List[Dict[str, Any]]:
        """Extrae transacciones; si se pasa `filename`, lee directamente del PDF."""
        if filename and pdfplumber:
            extracted_pages: List[str] = []
            with pdfplumber.open(filename) as pdf:
                for page in pdf.pages:
                    # ▸ delimitamos zona vertical válida
                    y0 = HEADER_HEIGHT
                    y1 = page.height - FOOTER_HEIGHT

                    # ▸ delimitamos columnas en coordenadas absolutas
                    split_x = page.width * SPLIT_RATIO
                    left_bbox = (0, y0, split_x - MARGIN_PT, y1)
                    right_bbox = (split_x + MARGIN_PT, y0, page.width, y1)

                    left_text = page.within_bbox(left_bbox).extract_text(x_tolerance=4, y_tolerance=2) or ""
                    right_text = page.within_bbox(right_bbox).extract_text(x_tolerance=4, y_tolerance=2) or ""
                    extracted_pages.append(left_text + "\n" + right_text)
            text = "\n".join(extracted_pages)

        # ------------------------------------------------------------------
        # PARSER DE LÍNEAS (heredado de v16)
        # ------------------------------------------------------------------
        lines = [ln for ln in text.splitlines() if ln.strip()]
        transactions: List[Dict[str, Any]] = []
        current_date = None

        for raw in lines:
            raw = raw.strip()

            maybe_date = parse_date(raw.split()[0])
            if maybe_date:
                current_date = maybe_date
                continue

            m_amt = AMOUNT_RE.search(raw)
            if not m_amt or current_date is None:
                if transactions:
                    transactions[-1]["description"] += " " + clean_text(raw)
                continue

            amount_raw = m_amt.group(0)
            desc_part = raw[: m_amt.start()].rstrip()

            if not CODE_LINE_RE.match(desc_part):
                if transactions:
                    transactions[-1]["description"] += " " + clean_text(raw)
                continue

            amt = float(_importe_roela(amount_raw))
            if _es_debito(desc_part):
                amt = -amt

            transactions.append(
                {
                    "date": current_date,
                    "description": clean_text(desc_part),
                    "amount": amt,
                    "currency": "ARS",
                    "bank": "Banco Roela (Arg.)",
                    "account": "",
                    "raw": raw,
                }
            )

        return transactions
