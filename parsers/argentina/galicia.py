from typing import List, Dict, Any
import re

from .base import ArgentinianBankParser
from utils import clean_text, parse_amount, parse_date

class GaliciaParser(ArgentinianBankParser):
    """Parser para Banco Galicia de Argentina."""

    bank_id = 'galicia'
    aliases = ['galicia']

    def _get_bank_name(self) -> str:
        return "Banco Galicia"

    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        transactions: List[Dict[str, Any]] = []
        account_info = self._extract_account_info(text_content)

        pattern = (
            r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+'
            r'([+-]?\d{1,3}(?:\.\d{3})*,\d{2})\s+'
            r'([+-]?\d{1,3}(?:\.\d{3})*,\d{2})'
        )

        for line in text_content.split('\n'):
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                try:
                    date_str = match.group(1)
                    description = clean_text(match.group(2))
                    amount_str = match.group(3)
                    balance_str = match.group(4)

                    parsed_date = parse_date(date_str)
                    if not parsed_date:
                        continue

                    amount = parse_amount(amount_str)
                    balance = parse_amount(balance_str)

                    transactions.append({
                        'date': parsed_date,
                        'description': description,
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
