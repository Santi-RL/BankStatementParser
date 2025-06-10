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
            r'Cuenta[:\s]+([0-9\s\-]+)',
            r'N°\s*([0-9\-\s]+)'
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
        elif any(currency in text_content.upper() for currency in ['ARS', 'AR$', 'PESO']):
            account_info['currency'] = 'ARS'
        
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

class GaliciaParser(SpanishBankParser):
    """Parser for Banco Galicia statements."""

    def _get_bank_name(self) -> str:
        return "Banco Galicia"

    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        transactions: List[Dict[str, Any]] = []
        account_info = self._extract_account_info(text_content)

        pattern = (
            r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+'  # date and description
            r'([+-]?\d{1,3}(?:\.\d{3})*,\d{2})\s+'  # amount
            r'([+-]?\d{1,3}(?:\.\d{3})*,\d{2})'      # balance
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

class GenericEnglishParser(BaseBankParser):
    """Parser for generic English bank statements."""
    
    def parse_transactions(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        """Parse generic English bank statement format."""
        transactions = []
        account_info = self._extract_account_info(text_content)
        
        # Check if this is a Chase format
        if 'chase' in text_content.lower() or 'jpmorgan' in text_content.lower():
            return self._parse_chase_format(text_content, filename, account_info)
        
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
    
    def _parse_chase_format(self, text_content: str, filename: str, account_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Parse Chase bank statement format."""
        transactions = []
        lines = text_content.split('\n')
        
        # Extract statement year from header
        statement_year = 2024
        for line in lines[:10]:
            years = re.findall(r'\b(20\d{2})\b', line)
            if years:
                statement_year = max(int(year) for year in years)
                break
        
        # Parse all transaction sections by looking for specific patterns
        current_section = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            line_lower = line.lower()
            
            # Identify sections
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
            
            # Skip headers
            if ('DATE' in line and 'DESCRIPTION' in line and 'AMOUNT' in line) or not line:
                continue
            
            # Parse transaction lines when in a valid section
            if current_section:
                # Look for lines that start with a date pattern
                date_match = re.match(r'^\s*(\d{1,2}/\d{1,2})\s+(.+)', line)
                if date_match:
                    try:
                        date_str = date_match.group(1)
                        rest_of_line = date_match.group(2)
                        
                        # Find amount at the end
                        amount_match = re.search(r'\$?([\d,]+\.\d{2})\s*$', rest_of_line)
                        if amount_match:
                            amount_str = amount_match.group(1).replace(',', '')
                            
                            # Extract description
                            amount_start = amount_match.start()
                            description = rest_of_line[:amount_start].strip()
                            description = clean_text(description)
                            
                            if len(description.strip()) < 3:
                                continue
                            
                            # Parse date
                            full_date = f"{date_str}/{statement_year}"
                            parsed_date = parse_date(full_date)
                            
                            if not parsed_date:
                                continue
                            
                            amount = parse_amount(amount_str)
                            
                            # Apply sign based on section
                            if current_section in ['withdrawals', 'fees']:
                                amount = -abs(amount)
                            else:
                                amount = abs(amount)
                            
                            transaction = {
                                'date': parsed_date,
                                'description': description,
                                'amount': amount,
                                'balance': '',
                                'account': account_info['account_number'],
                                'bank': "JPMorgan Chase",
                                'currency': 'USD',
                                'transaction_type': 'Credit' if amount > 0 else 'Debit'
                            }
                            
                            transactions.append(transaction)
                            
                    except (ValueError, IndexError) as e:
                        self.logger.debug(f"Failed to parse Chase line: {line}, error: {e}")
                        continue
        
        return transactions

class BankParserFactory:
    """Factory class to get appropriate bank parser."""
    
    def __init__(self):
        self.parsers = {
            'santander': SantanderParser(),
            'bbva': BBVAParser(),
            'caixabank': CaixaBankParser(),
            'galicia': GaliciaParser(),
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
