import pdfplumber
import PyPDF2
import re
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from bank_parsers import BankParserFactory
from utils import clean_text, parse_amount

class PDFProcessor:
    """Main PDF processing class that handles different bank statement formats."""
    
    def __init__(self):
        self.parser_factory = BankParserFactory()
        self.logger = logging.getLogger(__name__)
    
    def process_pdf(self, file_path: str, filename: str, debug: bool = False) -> Dict[str, Any]:
        """
        Process a PDF file and extract transaction data.
        
        Args:
            file_path: Path to the PDF file
            filename: Original filename for identification
            
        Returns:
            Dictionary containing success status, transactions, and metadata
        """
        steps: List[str] = []

        def log_step(step: str):
            if debug:
                steps.append(step)

        try:
            log_step("Extract text from PDF")
            text_content = self._extract_text_from_pdf(file_path)
            
            if not text_content:
                log_step("Failed to extract text")
                result = {
                    'success': False,
                    'error': 'Could not extract text from PDF. File may be image-based or corrupted.',
                    'transactions': [],
                    'bank_detected': 'Unknown'
                }
                if debug:
                    result['steps'] = steps
                return result
            
            log_step("Detect bank")
            bank_detected = self._detect_bank(text_content)
            log_step(f"Detected bank: {bank_detected}")
            parser = self.parser_factory.get_parser(bank_detected)
            
            if not parser:
                log_step("No parser available")
                result = {
                    'success': False,
                    'error': f'No parser available for detected bank: {bank_detected}',
                    'transactions': [],
                    'bank_detected': bank_detected
                }
                if debug:
                    result['steps'] = steps
                return result
            
            log_step("Parse transactions")
            transactions = parser.parse_transactions(text_content, filename)
            
            log_step("Validate transactions")
            valid_transactions = self._validate_transactions(transactions)
            log_step(f"Validated {len(valid_transactions)} transactions")
            
            result = {
                'success': True,
                'transactions': valid_transactions,
                'bank_detected': bank_detected,
                'total_transactions': len(valid_transactions)
            }
            if debug:
                result['steps'] = steps
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing PDF {filename}: {str(e)}")
            log_step(f"Exception: {str(e)}")
            result = {
                'success': False,
                'error': f'Processing error: {str(e)}',
                'transactions': [],
                'bank_detected': 'Unknown'
            }
            if debug:
                result['steps'] = steps
            return result
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text content from PDF file using multiple methods."""
        text_content = ""
        
        # Try pdfplumber first (better for complex layouts)
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
        except Exception as e:
            self.logger.warning(f"pdfplumber failed: {str(e)}")
        
        # Fallback to PyPDF2 if pdfplumber fails
        if not text_content.strip():
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"
            except Exception as e:
                self.logger.warning(f"PyPDF2 failed: {str(e)}")
        
        return clean_text(text_content)
    
    def _detect_bank(self, text_content: str) -> str:
        """
        Detect the bank based on text content patterns.
        
        Args:
            text_content: Extracted text from PDF
            
        Returns:
            Bank identifier string
        """
        text_lower = text_content.lower()
        
        # Spanish banks
        if any(keyword in text_lower for keyword in ['santander', 'banco santander']):
            return 'santander'
        elif any(keyword in text_lower for keyword in ['bbva', 'banco bilbao vizcaya']):
            return 'bbva'
        elif any(keyword in text_lower for keyword in ['caixabank', 'la caixa', 'caixa']):
            return 'caixabank'
        elif any(keyword in text_lower for keyword in ['bankia', 'banco de valencia']):
            return 'bankia'
        elif any(keyword in text_lower for keyword in ['banco sabadell', 'sabadell']):
            return 'sabadell'
        elif any(keyword in text_lower for keyword in ['unicaja', 'banco unicaja']):
            return 'unicaja'
        elif any(keyword in text_lower for keyword in ['kutxabank', 'kutxa']):
            return 'kutxabank'
        elif any(keyword in text_lower for keyword in ['ibercaja']):
            return 'ibercaja'
        
        # International banks
        elif any(keyword in text_lower for keyword in ['chase', 'jp morgan', 'jpmorgan']):
            return 'chase'
        elif any(keyword in text_lower for keyword in ['bank of america', 'bofa']):
            return 'bank_of_america'
        elif any(keyword in text_lower for keyword in ['wells fargo']):
            return 'wells_fargo'
        elif any(keyword in text_lower for keyword in ['citibank', 'citi']):
            return 'citibank'
        elif any(keyword in text_lower for keyword in ['hsbc']):
            return 'hsbc'
        elif any(keyword in text_lower for keyword in ['barclays']):
            return 'barclays'
        elif any(keyword in text_lower for keyword in ['deutsche bank']):
            return 'deutsche_bank'
        
        # Generic patterns
        elif any(keyword in text_lower for keyword in ['extracto', 'movimientos', 'cuenta corriente']):
            return 'generic_spanish'
        elif any(keyword in text_lower for keyword in ['statement', 'account activity', 'transaction history']):
            return 'generic_english'
        
        return 'unknown'
    
    def _validate_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean transaction data.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of validated transactions
        """
        valid_transactions = []
        
        for transaction in transactions:
            # Check required fields
            if not all(key in transaction for key in ['date', 'description', 'amount']):
                continue
            
            # Validate date
            if not self._is_valid_date(transaction.get('date')):
                continue
            
            # Validate amount
            try:
                amount = parse_amount(transaction.get('amount', '0'))
                transaction['amount'] = amount
            except (ValueError, TypeError):
                continue
            
            # Clean description
            transaction['description'] = clean_text(transaction.get('description', ''))
            
            # Ensure all required fields exist
            transaction.setdefault('balance', '')
            transaction.setdefault('transaction_type', self._determine_transaction_type(amount))
            transaction.setdefault('account', '')
            transaction.setdefault('bank', '')
            
            valid_transactions.append(transaction)
        
        return valid_transactions
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if date string is valid."""
        if not date_str:
            return False
        
        # Try common date formats
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
            '%d/%m/%y', '%d-%m-%y', '%y-%m-%d',
            '%d.%m.%Y', '%d.%m.%y',
            '%m/%d/%Y', '%m-%d-%Y'
        ]
        
        for fmt in date_formats:
            try:
                datetime.strptime(str(date_str), fmt)
                return True
            except ValueError:
                continue
        
        return False
    
    def _determine_transaction_type(self, amount: float) -> str:
        """Determine transaction type based on amount."""
        if amount > 0:
            return 'Credit'
        elif amount < 0:
            return 'Debit'
        else:
            return 'Neutral'
