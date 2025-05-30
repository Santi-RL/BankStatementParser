import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from utils import parse_amount, clean_text, parse_date

class BaseBankParser:
    """Base class for bank statement parsers."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        """
        Parse transactions from text content.
        
        Args:
            text_content: Extracted text from PDF
            filename: Original filename
            
        Returns:
            List of transaction dictionaries
        """
        raise NotImplementedError("Subclasses must implement parse_transactions")
    
    def _extract_account_info(self, text_content: str) -> Dict[str, str]:
        """Extract account information from text."""
        account_info = {
            'account_number': '',
            'account_holder': '',
            'currency': 'EUR'
        }
        
        # Common patterns for account numbers
        account_patterns = [
            r'N[úu]mero de cuenta[:\s]+([A-Z0-9\s\-]+)',
            r'Account number[:\s]+([A-Z0-9\s\-]+)',
            r'IBAN[:\s]+([A-Z0-9\s]+)',
            r'Cuenta[:\s]+([0-9\s\-]+)'
        ]
        
        for pattern in account_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                account_info['account_number'] = match.group(1).strip()
                break
        
        # Currency detection
        if any(currency in text_content.upper() for currency in ['USD', '$', 'DOLLAR']):
            account_info['currency'] = 'USD'
        elif any(currency in text_content.upper() for currency in ['GBP', '£', 'POUND']):
            account_info['currency'] = 'GBP'
        
        return account_info

class SpanishBankParser(BaseBankParser):
    """Parser for Spanish bank statements."""
    
    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        """Parse Spanish bank statement format."""
        transactions = []
        account_info = self._extract_account_info(text_content)
        
        # Common Spanish transaction patterns
        patterns = [
            # Pattern: DATE DESCRIPTION AMOUNT BALANCE
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(.+?)\s+([-+]?\d+[.,]\d{2})\s+([-+]?\d+[.,]\d{2})',
            # Pattern: DATE DESCRIPTION AMOUNT
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(.+?)\s+([-+]?\d+[.,]\d{2})',
            # Pattern with dots in thousands
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
                        
                        # Skip if description is too short or contains only numbers
                        if len(description) < 3 or description.isdigit():
                            continue
                        
                        # Parse date
                        parsed_date = parse_date(date_str)
                        if not parsed_date:
                            continue
                        
                        # Parse amounts
                        amount = parse_amount(amount_str)
                        balance = parse_amount(balance_str) if balance_str else None
                        
                        transaction = {
                            'date': parsed_date,
                            'description': description,
                            'amount': amount,
                            'balance': balance if balance is not None else '',
                            'account': account_info['account_number'],
                            'bank': self._get_bank_name(),
                            'currency': account_info['currency'],
                            'transaction_type': 'Credit' if amount > 0 else 'Debit'
                        }
                        
                        transactions.append(transaction)
                        break
                        
                    except (ValueError, IndexError) as e:
                        self.logger.debug(f"Failed to parse line: {line}, error: {e}")
                        continue
        
        return transactions
    
    def _get_bank_name(self) -> str:
        """Return the bank name for this parser."""
        return "Spanish Bank"

class SantanderParser(SpanishBankParser):
    """Parser specifically for Banco Santander statements."""
    
    def _get_bank_name(self) -> str:
        return "Banco Santander"
    
    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        """Parse Santander specific format."""
        # First try parent Spanish parser
        transactions = super().parse_transactions(text_content, filename)
        
        # If no transactions found, try Santander specific patterns
        if not transactions:
            transactions = self._parse_santander_specific(text_content, filename)
        
        return transactions
    
    def _parse_santander_specific(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        """Parse Santander specific patterns."""
        transactions = []
        account_info = self._extract_account_info(text_content)
        
        # Santander specific patterns
        santander_patterns = [
            r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([-+]?\d+,\d{2})\s+([-+]?\d+,\d{2})',
            r'(\d{2}-\d{2}-\d{4})\s+(.+?)\s+([-+]?\d+,\d{2})'
        ]
        
        lines = text_content.split('\n')
        
        for line in lines:
            for pattern in santander_patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        if len(match.groups()) >= 5:
                            # Format with operation date and value date
                            date_str = match.group(2)  # Value date
                            description = clean_text(match.group(3))
                            amount_str = match.group(4)
                            balance_str = match.group(5)
                        else:
                            # Simple format
                            date_str = match.group(1)
                            description = clean_text(match.group(2))
                            amount_str = match.group(3)
                            balance_str = ''
                        
                        parsed_date = parse_date(date_str)
                        if not parsed_date or len(description) < 3:
                            continue
                        
                        amount = parse_amount(amount_str)
                        balance = parse_amount(balance_str) if balance_str else None
                        
                        transaction = {
                            'date': parsed_date,
                            'description': description,
                            'amount': amount,
                            'balance': balance if balance is not None else '',
                            'account': account_info['account_number'],
                            'bank': self._get_bank_name(),
                            'currency': account_info['currency'],
                            'transaction_type': 'Credit' if amount > 0 else 'Debit'
                        }
                        
                        transactions.append(transaction)
                        break
                        
                    except (ValueError, IndexError):
                        continue
        
        return transactions

class BBVAParser(SpanishBankParser):
    """Parser for BBVA bank statements."""
    
    def _get_bank_name(self) -> str:
        return "BBVA"

class CaixaBankParser(SpanishBankParser):
    """Parser for CaixaBank statements."""
    
    def _get_bank_name(self) -> str:
        return "CaixaBank"

class GenericEnglishParser(BaseBankParser):
    """Parser for generic English bank statements."""
    
    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        """Parse generic English bank statement format."""
        transactions = []
        account_info = self._extract_account_info(text_content)
        
        # English transaction patterns
        patterns = [
            # Pattern: MM/DD/YYYY DESCRIPTION AMOUNT BALANCE
            r'(\d{1,2}/\d{1,2}/\d{4})\s+(.+?)\s+([-+]?\$?\d+[.,]\d{2})\s+([-+]?\$?\d+[.,]\d{2})',
            # Pattern: DD-MM-YYYY DESCRIPTION AMOUNT
            r'(\d{1,2}-\d{1,2}-\d{4})\s+(.+?)\s+([-+]?\$?\d+[.,]\d{2})',
            # Pattern with commas in thousands
            r'(\d{1,2}/\d{1,2}/\d{4})\s+(.+?)\s+([-+]?\$?\d{1,3}(?:,\d{3})*\.\d{2})'
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
                        amount_str = match.group(3).replace('$', '')
                        balance_str = match.group(4).replace('$', '') if len(match.groups()) >= 4 else ''
                        
                        if len(description) < 3 or description.isdigit():
                            continue
                        
                        parsed_date = parse_date(date_str)
                        if not parsed_date:
                            continue
                        
                        amount = parse_amount(amount_str)
                        balance = parse_amount(balance_str) if balance_str else None
                        
                        transaction = {
                            'date': parsed_date,
                            'description': description,
                            'amount': amount,
                            'balance': balance if balance is not None else '',
                            'account': account_info['account_number'],
                            'bank': "English Bank",
                            'currency': account_info['currency'],
                            'transaction_type': 'Credit' if amount > 0 else 'Debit'
                        }
                        
                        transactions.append(transaction)
                        break
                        
                    except (ValueError, IndexError):
                        continue
        
        return transactions

class BankParserFactory:
    """Factory class to get appropriate bank parser."""
    
    def __init__(self):
        self.parsers = {
            'santander': SantanderParser(),
            'bbva': BBVAParser(),
            'caixabank': CaixaBankParser(),
            'bankia': SpanishBankParser(),
            'sabadell': SpanishBankParser(),
            'unicaja': SpanishBankParser(),
            'kutxabank': SpanishBankParser(),
            'ibercaja': SpanishBankParser(),
            'generic_spanish': SpanishBankParser(),
            'generic_english': GenericEnglishParser(),
            'chase': GenericEnglishParser(),
            'bank_of_america': GenericEnglishParser(),
            'wells_fargo': GenericEnglishParser(),
            'citibank': GenericEnglishParser(),
            'hsbc': GenericEnglishParser(),
            'barclays': GenericEnglishParser(),
            'deutsche_bank': GenericEnglishParser(),
        }
    
    def get_parser(self, bank_identifier: str) -> Optional[BaseBankParser]:
        """
        Get appropriate parser for the detected bank.
        
        Args:
            bank_identifier: Bank identifier string
            
        Returns:
            Bank parser instance or None
        """
        parser = self.parsers.get(bank_identifier)
        if not parser and bank_identifier != 'unknown':
            # Fallback to generic parsers
            if any(keyword in bank_identifier.lower() for keyword in ['spanish', 'spain', 'españa']):
                parser = self.parsers['generic_spanish']
            else:
                parser = self.parsers['generic_english']
        
        return parser
