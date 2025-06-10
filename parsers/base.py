import re
from typing import List, Dict, Any
import logging

class BaseBankParser:
    """Clase base para los parsers de extractos bancarios."""

    bank_id: str = ""
    aliases: List[str] = []

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        """Parsear las transacciones a partir del texto extraído."""
        raise NotImplementedError("Subclasses must implement parse_transactions")

    def _extract_account_info(self, text_content: str) -> Dict[str, str]:
        """Extraer información de la cuenta del texto."""
        account_info = {
            'account_number': '',
            'account_holder': '',
            'currency': 'EUR'
        }

        account_patterns = [
            r'N[úu]mero de cuenta[:\s]+([A-Z0-9\s\-]+)',
            r'Account number[:\s]+([A-Z0-9\s\-]+)',
            r'IBAN[:\s]+([A-Z0-9\s]+)',
            r'Cuenta[:\s]+([0-9\s\-]+)',
            r'N°\s*([0-9\-\s]+)'
        ]

        for pattern in account_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                account_info['account_number'] = match.group(1).strip()
                break

        if any(c in text_content.upper() for c in ['USD', '$', 'DOLLAR']):
            account_info['currency'] = 'USD'
        elif any(c in text_content.upper() for c in ['GBP', '£', 'POUND']):
            account_info['currency'] = 'GBP'
        elif any(c in text_content.upper() for c in ['ARS', 'AR$', 'PESO']):
            account_info['currency'] = 'ARS'

        return account_info
