from __future__ import annotations

"""
roela_ar.py – Parser para extractos del **Banco Roela (Argentina)**
=================================================================
Versión v24 (jul‑2025)
-----------------------------------------------------------------
* **Corrección de filtrado**: se descartan líneas de saldo/balance
  (ej. "SALDO AL 02/09/2024 ...") y, en general, cualquier línea cuyo primer
  token no sea un código de transacción válido según `_CODE_RE`.
* Mantiene el algoritmo de signos basado en códigos (v23).
"""

import re
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional

try:
    import pdfplumber
except Exception:  # pragma: no cover – optional dependency
    pdfplumber = None

from .base import ArgentinianBankParser
from utils import clean_text, parse_date

# ───────────────────── Configuración de recorte ──────────────────────
HEADER_CUT: float = 260.0     # puntos desde el BOTTOM (pie de página)
FOOTER_CUT: float = 30.0      # puntos desde el TOP    (cabecera)
SPLIT_RATIO: float = 0.515    # 51,5 % a la izquierda, resto derecha
MARGIN_PT: float = 0        # tolerancia entre columnas

# ───────────────────── Reglas de signos por código ────────────────────
# 1) Excepciones explícitas 100 % débito / crédito
_DEBIT_EXPLICIT = {
    "309", "313", "314", "317", "318", "319", "320", "321", "322", "323",
    "386", "396", "300100", "700100", "710100", "750100", "760100", "810100",
    "860100", "880100", "F30100",
}

_CREDIT_EXPLICIT = {
    "305", "310", "324", "325", "332", "333", "334", "335",
    "720100", "740100", "770100", "F40001",
}

# 2) Prefijos con regla general + excepciones
_PREFIX_RULES: Dict[str, Dict[str, Any]] = {
    "1": {"default": "D"},
    "2": {"default": "D", "credit": {"290", "291", "296", "200001", "240001", "290001"}},
    "4": {"default": "C", "debit": {"400101", "400111"}},
    "5": {"default": "C", "debit": {"557", "583", "585", "586", "593", "594", "500131"}},
}

_CODE_RE = re.compile(r"^[A-Za-z]?\d+$")  # p.e. "F40001", "148"


def _is_debit(code: str) -> bool:
    """Devuelve *True* si el movimiento es débito (importe negativo)."""
    code = code.strip()
    if code in _DEBIT_EXPLICIT:
        return True
    if code in _CREDIT_EXPLICIT:
        return False

    if not _CODE_RE.match(code):
        # Código inesperado → asumimos débito
        return True

    num_part = code.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    prefix = num_part[0]
    rules = _PREFIX_RULES.get(prefix)
    if not rules:
        return True  # prefijo desconocido → débito

    if "credit" in rules and num_part in rules["credit"]:
        return False
    if "debit" in rules and num_part in rules["debit"]:
        return True

    return rules["default"] == "D"

# ───────────────────── RegEx auxiliares ───────────────────────────────
AMOUNT_RE = re.compile(r"-?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}")
DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
ACCOUNT_RE = re.compile(r"Cuenta\s*:\s*(\d+/\d+)")  # Para capturar "22537/8"

# ───────────────────── Utilidades propias ─────────────────────────────

def _parse_amount(amount_str: str) -> Decimal:
    """Normaliza el importe → Decimal(2) manteniendo signo."""
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

# ───────────────────── Excepciones ─────────────────────────────────
class EndOfRelevantPagesError(Exception):
    """Señaliza que se alcanzó la sección no relevante del extracto."""
    pass

# ───────────────────── Parser principal ───────────────────────────────


class RoelaParser(ArgentinianBankParser):
    """Parser específico para Banco Roela (ARS)."""

    bank_id = "roela_ar"
    aliases = ["roela"]

    def _get_bank_name(self) -> str:
        return "Banco Roela (Arg.)"

    # ------------------------------------------------------------------
    # Extracción de texto
    # ------------------------------------------------------------------
    def _extract_page_text(self, page) -> str:
        """Intenta recortar columnas y, si falla, extrae la página completa."""
        # Primero extraemos el texto completo de la página para verificar si contiene el texto a excluir
        full_text = page.extract_text() or ""
        if "DE INTERES PARA USTED" in full_text.upper():
            raise EndOfRelevantPagesError()
            
        try:
            y0 = HEADER_CUT
            y1 = page.height - FOOTER_CUT
            split_x = page.width * SPLIT_RATIO
            left_bbox = (0, y0, split_x - MARGIN_PT, y1)
            right_bbox = (split_x + MARGIN_PT, y0, page.width, y1)

            left_text = page.within_bbox(left_bbox).extract_text(x_tolerance=4, y_tolerance=2) or ""
            right_text = page.within_bbox(right_bbox).extract_text(x_tolerance=4, y_tolerance=2) or ""
            merged = (left_text + "\n" + right_text).strip()
            if merged:
                return merged
        except Exception:
            pass
        return full_text

    # ------------------------------------------------------------------
    # Entrada pública
    # ------------------------------------------------------------------
    def parse_transactions(self, text: str, filename: Optional[str] = None, **_) -> List[Dict[str, Any]]:
        account_number = ""
        
        # 1) Re‑extraemos texto desde el PDF si lo tenemos
        if filename and pdfplumber:
            pages_text: List[str] = []
            try:
                with pdfplumber.open(filename) as pdf:
                    # Extraemos el número de cuenta de la primera página
                    if pdf.pages:
                        first_page_text = pdf.pages[0].extract_text() or ""
                        account_match = ACCOUNT_RE.search(first_page_text)
                        if account_match:
                            account_number = account_match.group(1)
                    
                    # Continuamos con la extracción normal de páginas
                    for page in pdf.pages:
                        pages_text.append(self._extract_page_text(page))
            except EndOfRelevantPagesError:
                pass  # Detenemos el procesamiento pero continuamos con las páginas ya extraídas
            text = "\n".join(pages_text)

        # 2) Normalizamos y dividimos en líneas
        lines = [ln for ln in text.splitlines() if ln.strip()]

        transactions: List[Dict[str, Any]] = []
        current_date: Optional[str] = None

        for raw in lines:
            raw = raw.strip()
            tokens = raw.split()
            if not tokens:
                continue

            # (a) Línea de fecha
            if DATE_RE.match(tokens[0]):
                parsed = parse_date(tokens[0])
                if parsed:
                    current_date = parsed
                continue

            # (b) Balance/saldo → omitir
            if tokens[0].upper() == "SALDO":
                continue

            # (c) Localizamos importe
            m_amt = AMOUNT_RE.search(raw)
            if not m_amt or current_date is None:
                # Continuación de descripción
                if transactions:
                    transactions[-1]["description"] += " " + clean_text(raw)
                continue

            amount_raw = m_amt.group(0)
            amount_dec = _parse_amount(amount_raw)

            # Parte descriptiva antes del importe
            desc_part = raw[: m_amt.start()].rstrip()
            desc_part_clean = clean_text(desc_part)

            # Primer token: código
            code = desc_part_clean.split(" ")[0]

            # Verificación de código válido; si no lo es, omitimos (ej. SALDOS)
            if not _CODE_RE.match(code):
                continue

            sign = -1 if _is_debit(code) else 1

            transactions.append(
                {
                    "date": current_date,
                    "description": desc_part_clean,
                    "amount": float(amount_dec) * sign,
                    "currency": "ARS",
                    "bank": "Banco Roela (Arg.)",
                    "account": account_number,
                    "raw": raw,
                }
            )

        return transactions
