from typing import List, Dict, Any
import re

from .base import BaseBankParser
from utils import parse_amount, clean_text, parse_date

class GenericEnglishParser(BaseBankParser):
    """Parser genérico para extractos en inglés."""

    bank_id = 'generic_english'
    aliases = [
        'generic_english', 'chase', 'bank_of_america', 'wells_fargo', 'citibank',
        'hsbc', 'barclays', 'deutsche_bank'
    ]

    def _get_bank_name(self) -> str:
        return "English Bank"

    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        transactions: List[Dict[str, Any]] = []
        account_info = self._extract_account_info(text_content)

        if 'chase' in text_content.lower() or 'jpmorgan' in text_content.lower():
            return self._parse_chase_format(text_content, filename, account_info)

        patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})\s+(.+?)\s+([-+]?\$?\d+[.,]\d{2})\s+([-+]?\$?\d+[.,]\d{2})',
            r'(\d{1,2}-\d{1,2}-\d{4})\s+(.+?)\s+([-+]?\$?\d+[.,]\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})\s+(.+?)\s+([-+]?\$?\d{1,3}(?:,\d{3})*\.\d{2})'
        ]

        for line in text_content.split('\n'):
            line = line.strip()
            if not line:
                continue
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        date_str = match.group(1)
                        description = clean_text(match.group(2))
                        amount_str = match.group(3).replace('$', '')
                        balance_str = match.group(4).replace('$', '') if len(match.groups()) >= 4 else ''

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
                    except (ValueError, IndexError):
                        continue
        return transactions

    def _parse_chase_format(self, text_content: str, filename: str, account_info: Dict[str, str]) -> List[Dict[str, Any]]:
        transactions: List[Dict[str, Any]] = []
        lines = text_content.split('\n')

        statement_year = 2024
        for line in lines[:10]:
            years = re.findall(r'\b(20\d{2})\b', line)
            if years:
                statement_year = max(int(year) for year in years)
                break

        current_section = None
        for line in lines:
            line = line.strip()
            line_lower = line.lower()
            if 'deposits and additions' in line_lower:
                current_section = 'deposits'
                continue
            elif 'electronic withdrawals' in line_lower:
                current_section = 'withdrawals'
                continue
            elif line_lower.strip() == 'fees':
                current_section = 'fees'
                continue
            elif line.startswith('Total '):
                current_section = None
                continue

            if ('DATE' in line and 'DESCRIPTION' in line and 'AMOUNT' in line) or not line:
                continue

            if current_section:
                date_match = re.match(r'^\s*(\d{1,2}/\d{1,2})\s+(.+)', line)
                if date_match:
                    try:
                        date_str = date_match.group(1)
                        rest_of_line = date_match.group(2)
                        amount_match = re.search(r'\$?([\d,]+\.\d{2})\s*$', rest_of_line)
                        if amount_match:
                            amount_str = amount_match.group(1).replace(',', '')
                            amount_start = amount_match.start()
                            description = rest_of_line[:amount_start].strip()
                            description = clean_text(description)

                            if len(description.strip()) < 3:
                                continue

                            full_date = f"{date_str}/{statement_year}"
                            parsed_date = parse_date(full_date)
                            if not parsed_date:
                                continue

                            amount = parse_amount(amount_str)
                            if current_section in ['withdrawals', 'fees']:
                                amount = -abs(amount)
                            else:
                                amount = abs(amount)

                            transactions.append({
                                'date': parsed_date,
                                'description': description,
                                'amount': amount,
                                'balance': '',
                                'account': account_info['account_number'],
                                'bank': "JPMorgan Chase",
                                'currency': 'USD',
                                'transaction_type': 'Credit' if amount > 0 else 'Debit'
                            })
                    except (ValueError, IndexError) as e:
                        self.logger.debug(f"Failed to parse Chase line: {line}, error: {e}")
                        continue
        return transactions
