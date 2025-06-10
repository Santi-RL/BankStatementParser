from typing import List, Dict, Any
import re

from ..base import BaseBankParser
from utils import parse_amount, clean_text, parse_date

class SpanishBankParser(BaseBankParser):
    """Parser genérico para extractos de bancos españoles."""

    bank_id = "generic_spanish"
    aliases = [
        'bankia', 'sabadell', 'unicaja', 'kutxabank', 'ibercaja', 'generic_spanish'
    ]

    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        transactions: List[Dict[str, Any]] = []
        account_info = self._extract_account_info(text_content)

        patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(.+?)\s+([-+]?\d+[.,]\d{2})\s+([-+]?\d+[.,]\d{2})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(.+?)\s+([-+]?\d+[.,]\d{2})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(.+?)\s+([-+]?\d{1,3}(?:\.\d{3})*,\d{2})'
        ]

        lines = text_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        date_str = match.group(1)
                        description = clean_text(match.group(2))
                        amount_str = match.group(3)
                        balance_str = match.group(4) if len(match.groups()) >= 4 else ''

                        if len(description) < 3 or description.isdigit():
                            continue

                        parsed_date = parse_date(date_str)
                        if not parsed_date:
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
                    except (ValueError, IndexError) as e:
                        self.logger.debug(f"Failed to parse line: {line}, error: {e}")
                        continue
        return transactions

    def _get_bank_name(self) -> str:
        return "Spanish Bank"
