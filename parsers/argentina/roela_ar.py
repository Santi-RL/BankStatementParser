from typing import List, Dict, Any
import re
from decimal import Decimal, InvalidOperation

try:
    import pdfplumber
except Exception:  # pragma: no cover – optional dependency
    pdfplumber = None

from .base import ArgentinianBankParser
from utils import clean_text, parse_date


# ---------- Conversión de importes 1,000.00 → Decimal -----------------------
def _importe_roela(amount_str: str) -> Decimal:
    num = amount_str.replace(",", "").strip()
    try:
        return Decimal(num)
    except InvalidOperation:
        return Decimal("0.00")


# ---------- Palabras/códigos que indican débito -----------------------------
DEBIT_WORDS = ("COM.", "IMPUESTO", "I.V.A", "IVA")

def _es_debito(desc: str) -> bool:
    desc_up = desc.upper()
    return desc_up.startswith(DEBIT_WORDS) or re.match(r"^\d{3}\s", desc_up)


# ---------- Parámetros para recorte y extracción ----------------------------
SPLIT_RATIO = 0.50   # % del ancho para la columna izquierda
MARGIN      = 3      # puntos: se suma a izq. y se resta a der.
CHAR_MARGIN = 4      # agrupa caracteres separados ≤ 4 pt


class RoelaParser(ArgentinianBankParser):
    """Parser para Banco Roela de Argentina."""

    bank_id = "roela_ar"
    aliases = ["roela"]

    # --------------------------------------------------------------------- #
    def _get_bank_name(self) -> str:
        return "Banco Roela (Arg.)"

    # --------------------------------------------------------------------- #
    def parse_transactions(
        self, text_content: str, filename: str
    ) -> List[Dict[str, Any]]:
        extracted = text_content
        # Extraer datos de cuenta/moneda antes de recortar
        account_info = self._extract_account_info(text_content)

        # ---------------- Recorte de columnas -----------------------------
        if pdfplumber is not None and filename:
            try:
                with pdfplumber.open(filename) as pdf:
                    extracted = ""
                    for page in pdf.pages:
                        split_x = page.width * SPLIT_RATIO

                        left_page  = page.crop((0,               0,
                                                split_x + MARGIN, page.height))
                        right_page = page.crop((split_x - MARGIN, 0,
                                                page.width,      page.height))

                        for section in (left_page, right_page):
                            text = section.extract_text(
                                char_margin=CHAR_MARGIN
                            )
                            if text:
                                extracted += text + "\n"
            except Exception:
                extracted = text_content

        # ---------------- Parseo de movimientos ---------------------------
        transactions: List[Dict[str, Any]] = []

        # Insertar salto antes de cada fecha
        extracted = re.sub(r"(\d{2}/\d{2}/\d{4})", r"\n\1", extracted)
        parts = re.split(r"(\d{2}/\d{2}/\d{4})", extracted)

        tx_pattern = re.compile(
            r"(?:\d{3}|[A-Z0-9]{5,6})\s+\d+\s+"          # prefijo flexible
            r"(.+?)\s+"                                  # descripción
            r"([+-]?\d{1,3}(?:,\d{3})*\.\d{2})"          # importe 1,000.00
            r"(?:\s|$)",
            re.MULTILINE,
        )

        for i in range(1, len(parts), 2):
            date_str = parts[i]
            body = parts[i + 1]

            if "SALDO" in body.upper() or "RESUMEN" in body.upper():
                continue

            parsed_date = parse_date(date_str)
            if not parsed_date:
                continue

            for match in tx_pattern.finditer(body):
                desc, amount_str = match.groups()
                desc = clean_text(desc)
                if len(desc) < 3:
                    continue

                amount   = _importe_roela(amount_str)
                is_debit = _es_debito(desc)
                if is_debit:
                    amount = -amount

                transactions.append({
                    "date": parsed_date,
                    "description": desc,
                    "amount": amount,
                    "balance": "",
                    "account": account_info.get("account_number", ""),
                    "bank": self._get_bank_name(),
                    "currency": account_info.get("currency", ""),
                    "transaction_type": "Debit" if is_debit else "Credit",
                })

        # Fallback genérico si no se encontró nada
        if not transactions:
            transactions = super().parse_transactions(extracted, filename)

        return transactions
