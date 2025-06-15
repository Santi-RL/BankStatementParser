from __future__ import annotations

"""
roela_ar.py – Parser para extractos del **Banco Roela (Argentina)**
=================================================================
Versión v16 (17 jun 2025)
------------------------
* Base: v14 (salto de pie «Fecha de Impresión…» → «CODIGO»).
* **Fix columnas**: el salto de pie se aplica **dentro de cada columna**
  antes de concatenar. Así se preservan las filas válidas de la columna
  derecha, que antes quedaban descartadas.
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

# ───────────────────── Configuración de corte de columnas ──────────────────────
SPLIT_RATIO: float = 0.515   # 51.5 % a la izquierda, 48.5 % a la derecha
MARGIN_PT: int = 0           # sin margen extra

# ───────────────────── Regex y helpers ─────────────────────────────────────────
AMOUNT_RE = re.compile(r"-?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}")
CODE_LINE_RE = re.compile(r"^[A-Z0-9]{1,6}\s+[0-9]{1,15}\b", re.ASCII)
FOOTER_START_RE = re.compile(r"FECHA\s+DE\s+IMPRES", re.I)  # dentro de línea
HEADER_CODIGO_RE = re.compile(r"^CODIGO\b", re.I)

_DEBIT_HINTS = (
    "IMPUESTO",
    "COM.",
    "IVA",
    "DEBITO",
    "DÉBITO",
)


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


def _es_debito(desc: str) -> bool:
    up = desc.upper()
    return any(tok in up for tok in _DEBIT_HINTS)


def _strip_footer(col_text: str) -> str:
    """Retorna sólo la parte de la columna antes de 'Fecha de Impresión'."""
    m = FOOTER_START_RE.search(col_text)
    return col_text[: m.start()] if m else col_text


class RoelaParser(ArgentinianBankParser):
    bank_id = "roela_ar"
    aliases = ["roela"]

    def parse_transactions(
        self, text: str, filename: str | None = None, **_
    ) -> List[Dict[str, Any]]:

        # 1. Recortar columnas si tenemos PDF
        if filename and pdfplumber:
            parts: List[str] = []
            with pdfplumber.open(filename) as pdf:
                for page in pdf.pages:
                    w, h = page.width, page.height
                    split_x = w * SPLIT_RATIO
                    left_box = (0, 0, split_x - MARGIN_PT, h)
                    right_box = (split_x + MARGIN_PT, 0, w, h)
                    left = page.within_bbox(left_box).extract_text(x_tolerance=4, y_tolerance=2) or ""
                    right = page.within_bbox(right_box).extract_text(x_tolerance=4, y_tolerance=2) or ""
                    parts.append(_strip_footer(left) + "\n" + _strip_footer(right))
            text = "\n".join(parts)

        # 2. Procesar línea a línea
        lines = [ln for ln in text.splitlines() if ln.strip()]
        txs: List[Dict[str, Any]] = []
        current_date = None

        for raw in lines:
            raw = raw.strip()
            up_raw = raw.upper()

            # — Cortar cualquier resto de pie dentro de la misma línea —
            idx_footer = up_raw.find("FECHA DE IMPRES")
            if idx_footer != -1:
                if idx_footer == 0:
                    continue  # la línea ES pie → descartar
                raw = raw[:idx_footer].rstrip()
                up_raw = raw.upper()
                if not raw:
                    continue

            # 2.a Línea que es sólo fecha
            maybe_date = parse_date(raw.split()[0])
            if maybe_date:
                current_date = maybe_date
                continue

            # 2.b Buscar importe
            m = AMOUNT_RE.search(raw)
            if not m or current_date is None:
                if txs:
                    txs[-1]["description"] += " " + clean_text(raw)
                continue

            amount_raw = m.group(0)
            desc_part = raw[: m.start()].rstrip()

            # 2.c Validar fila válida
            if not CODE_LINE_RE.match(desc_part):
                if txs:
                    txs[-1]["description"] += " " + clean_text(raw)
                continue

            amount = float(_importe_roela(amount_raw))
            if _es_debito(desc_part):
                amount = -amount

            txs.append(
                {
                    "date": current_date,
                    "description": clean_text(desc_part),
                    "amount": amount,
                    "currency": "ARS",
                    "bank": "Banco Roela (Arg.)",
                    "account": "",
                    "raw": raw,
                }
            )

        return txs
