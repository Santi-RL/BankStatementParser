from typing import List, Dict, Any
import re

from .base import SpanishBankParser
from utils import clean_text, parse_amount, parse_date

class SantanderParser(SpanishBankParser):
    """Parser para los extractos de Banco Santander."""

    bank_id = 'santander'
    aliases = ['santander']

    def _get_bank_name(self) -> str:
        return "Banco Santander"

    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        transactions = super().parse_transactions(text_content, filename)
        if not transactions:
            transactions = self._parse_santander_specific(text_content, filename)
        return transactions

    def _parse_santander_specific(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        transactions: List[Dict[str, Any]] = []
        account_info = self._extract_account_info(text_content)

        patterns = [
            r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([-+]?\d+,\d{2})\s+([-+]?\d+,\d{2})',
            r'(\d{2}-\d{2}-\d{4})\s+(.+?)\s+([-+]?\d+,\d{2})'
        ]

        for line in text_content.split('\n'):
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        if len(match.groups()) >= 5:
                            date_str = match.group(2)
                            description = clean_text(match.group(3))
                            amount_str = match.group(4)
                            balance_str = match.group(5)
                        else:
                            date_str = match.group(1)
                            description = clean_text(match.group(2))
                            amount_str = match.group(3)
                            balance_str = ''

                        parsed_date = parse_date(date_str)
                        if not parsed_date or len(description) < 3:
                            continue

                        amount = parse_amount(amount_str)
                        balance = parse_amount(balance_str) if balance_str else None

                        transactions.append({
                            'date': parsed_date,
                            'description': description,
                            'amount': amount,
                            'balance': balance if balance is not None else '',
                            'account': account_info['account_number'],
                            'bank': self._get_bank_name(),
                            'currency': account_info['currency'],
                            'transaction_type': 'Credit' if amount > 0 else 'Debit'
                        })
                        break
                    except (ValueError, IndexError):
                        continue
        return transactions
