from typing import List, Dict, Any, Optional
import re

from .base import ArgentinianBankParser
from utils import clean_text, parse_amount, parse_date

class GaliciaParser(ArgentinianBankParser):
    """Parser para Banco Galicia de Argentina."""

    bank_id = 'galicia_ar'
    aliases = ['galicia']

    def _get_bank_name(self) -> str:
        return "Banco Galicia (Arg.)"

    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        transactions: List[Dict[str, Any]] = []
        account_info = self._extract_account_info(text_content)

        start_tx_re = re.compile(
            r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+'
            r'([+-]?\d{1,3}(?:\.\d{3})*,\d{2})\s+'
            r'([+-]?\d{1,3}(?:\.\d{3})*,\d{2})'
        )

        current_match: Optional[re.Match] = None
        desc_lines: List[str] = []

        for raw_line in text_content.split('\n'):
            line = raw_line.strip()
            if not line:
                continue

            match = start_tx_re.match(line)
            if match:
                if current_match:
                    try:
                        date_str = current_match.group(1)
                        base_desc = clean_text(current_match.group(2))
                        amount_str = current_match.group(3)
                        balance_str = current_match.group(4)
                        parsed_date = parse_date(date_str)
                        if parsed_date:
                            amount = parse_amount(amount_str)
                            balance = parse_amount(balance_str)
                            full_desc = base_desc
                            if desc_lines:
                                full_desc += ' ' + ' '.join(desc_lines)
                            transactions.append({
                                'date': parsed_date,
                                'description': full_desc,
                                'amount': amount,
                                'balance': balance,
                                'account': account_info['account_number'],
                                'bank': self._get_bank_name(),
                                'currency': account_info['currency'],
                                'transaction_type': 'Credit' if amount > 0 else 'Debit'
                            })
                    except (ValueError, IndexError) as e:
                        self.logger.debug(f"Failed to parse line: {line}, error: {e}")

                current_match = match
                desc_lines = []
                continue

            if current_match:
                if re.match(r'^(Resumen de Caja|Página|Fecha\s+Descripción|Movimientos|Datos de la cuenta)', line, re.IGNORECASE):
                    continue
                if re.match(r'^\d{2}/\d{2}/\d{2}', line):
                    # Nuevo inicio que no coincidió completamente, procesar existente
                    try:
                        date_str = current_match.group(1)
                        base_desc = clean_text(current_match.group(2))
                        amount_str = current_match.group(3)
                        balance_str = current_match.group(4)
                        parsed_date = parse_date(date_str)
                        if parsed_date:
                            amount = parse_amount(amount_str)
                            balance = parse_amount(balance_str)
                            full_desc = base_desc
                            if desc_lines:
                                full_desc += ' ' + ' '.join(desc_lines)
                            transactions.append({
                                'date': parsed_date,
                                'description': full_desc,
                                'amount': amount,
                                'balance': balance,
                                'account': account_info['account_number'],
                                'bank': self._get_bank_name(),
                                'currency': account_info['currency'],
                                'transaction_type': 'Credit' if amount > 0 else 'Debit'
                            })
                    except (ValueError, IndexError) as e:
                        self.logger.debug(f"Failed to parse line: {line}, error: {e}")

                    current_match = None
                    desc_lines = []
                    # Re-evaluar la línea actual por si es un nuevo comienzo válido
                    match = start_tx_re.match(line)
                    if match:
                        current_match = match
                    continue

                desc_lines.append(clean_text(line))

        if current_match:
            try:
                date_str = current_match.group(1)
                base_desc = clean_text(current_match.group(2))
                amount_str = current_match.group(3)
                balance_str = current_match.group(4)
                parsed_date = parse_date(date_str)
                if parsed_date:
                    amount = parse_amount(amount_str)
                    balance = parse_amount(balance_str)
                    full_desc = base_desc
                    if desc_lines:
                        full_desc += ' ' + ' '.join(desc_lines)
                    transactions.append({
                        'date': parsed_date,
                        'description': full_desc,
                        'amount': amount,
                        'balance': balance,
                        'account': account_info['account_number'],
                        'bank': self._get_bank_name(),
                        'currency': account_info['currency'],
                        'transaction_type': 'Credit' if amount > 0 else 'Debit'
                    })
            except (ValueError, IndexError) as e:
                self.logger.debug(f"Failed to parse line: {line}, error: {e}")

        if not transactions:
            transactions = super().parse_transactions(text_content, filename)
        return transactions
