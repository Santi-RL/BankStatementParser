from typing import List, Dict, Any
import re

try:
    import pdfplumber
except Exception:  # pragma: no cover - optional dependency
    pdfplumber = None

from .base import ArgentinianBankParser
from utils import clean_text, parse_amount, parse_date


class RoelaParser(ArgentinianBankParser):
    """Parser para Banco Roela de Argentina."""

    bank_id = "roela_ar"
    aliases = ["roela"]

    def _get_bank_name(self) -> str:
        return "Banco Roela (Arg.)"

    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        extracted = text_content
        if pdfplumber is not None and filename:
            try:
                with pdfplumber.open(filename) as pdf:
                    extracted = ""
                    for page in pdf.pages:
                        # --- Nuevo método: usar crop() como en el script probado ---
                        left_text = page.crop((0, 0, page.width / 2, page.height)).extract_text()
                        right_text = page.crop((page.width / 2, 0, page.width, page.height)).extract_text()

                        # Concatenar primero la izquierda y luego la derecha
                        for page_text in (left_text, right_text):
                            if page_text:
                                extracted += page_text + "\n"
            except Exception:
                # Si falla la lectura del PDF, usar el texto proporcionado
                extracted = text_content

        transactions: List[Dict[str, Any]] = []
        account_info = self._extract_account_info(extracted)

        # Normalizar el texto insertando saltos de línea antes de cada fecha
        extracted = re.sub(r"(\d{2}/\d{2}/\d{4})", r"\n\1", extracted)

        # Dividir en segmentos "fecha + contenido" para procesar múltiples
        # movimientos que comparten la misma fecha
        parts = re.split(r"(\d{2}/\d{2}/\d{4})", extracted)

        tx_pattern = re.compile(
            r"(?:[A-Z0-9]{5}\s+\d+\s+)?([^\d\n]+?)\s+"
            r"([+-]?\d{1,3}(?:,\d{3})*\.\d{2}|[+-]?\d{1,3}(?:\.\d{3})*,\d{2})"
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
                amount = parse_amount(amount_str)
                transactions.append({
                    "date": parsed_date,
                    "description": desc,
                    "amount": amount,
                    "balance": "",
                    "account": account_info["account_number"],
                    "bank": self._get_bank_name(),
                    "currency": account_info["currency"],
                    "transaction_type": "Credit" if amount > 0 else "Debit",
                })

        if not transactions:
            transactions = super().parse_transactions(extracted, filename)

        return transactions
