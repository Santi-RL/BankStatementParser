import pdfplumber
import PyPDF2
import logging
from typing import Dict, List, Any, Optional
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
            file_path (str): Path to the PDF file.
            filename (str): Original filename for identification.
            debug (bool): When True, returns a debug_log list describing each processing stage.

        Returns:
            Dict[str, Any]: Dictionary containing success status, transactions, metadata,
                and debug_log if debug is True.
        """
        debug_log: Optional[List[str]] = [] if debug else None

        try:
            # Inicializar debug log
            if debug and debug_log is not None:
                debug_log.append(f"Starting processing for {filename}")
                debug_log.append("Beginning text extraction")

            # Extraer texto del PDF
            text_content = self._extract_text_from_pdf(file_path, debug_log)
            if debug and debug_log is not None:
                debug_log.append("Finished text extraction")

            # Si no hay texto extraído
            if not text_content:
                result = {
                    'success': False,
                    'error': 'Could not extract text from PDF. File may be image-based or corrupted.',
                    'transactions': [],
                    'bank_detected': 'Unknown',
                }
                if debug and debug_log is not None:
                    debug_log.append("Failed to extract text")
                    result['debug_log'] = debug_log
                return result

            # Detectar banco
            if debug and debug_log is not None:
                debug_log.append("Detecting bank")
            bank_detected = self._detect_bank(text_content)
            if debug and debug_log is not None:
                debug_log.append(f"Detected bank: {bank_detected}")

            # Obtener parser
            parser = self.parser_factory.get_parser(bank_detected)
            if not parser:
                result = {
                    'success': False,
                    'error': f'No parser available for detected bank: {bank_detected}',
                    'transactions': [],
                    'bank_detected': bank_detected,
                }
                if debug and debug_log is not None:
                    debug_log.append(f"No parser found for bank: {bank_detected}")
                    result['debug_log'] = debug_log
                return result

            # Parsear transacciones
            if debug and debug_log is not None:
                debug_log.append("Parsing transactions")
            transactions = parser.parse_transactions(text_content, filename)
            if debug and debug_log is not None:
                debug_log.append(f"Parsed {len(transactions)} transactions")

            # Validar transacciones
            if debug and debug_log is not None:
                debug_log.append("Validating transactions")
            valid_transactions = self._validate_transactions(transactions)
            if debug and debug_log is not None:
                debug_log.append(f"Validation complete, {len(valid_transactions)} valid transactions")

            # Construir resultado exitoso
            result = {
                'success': True,
                'transactions': valid_transactions,
                'bank_detected': bank_detected,
                'total_transactions': len(valid_transactions),
            }
            if debug and debug_log is not None:
                result['debug_log'] = debug_log
            return result

        except Exception as e:
            self.logger.error(f"Error processing PDF {filename}: {e}")
            result = {
                'success': False,
                'error': f'Processing error: {e}',
                'transactions': [],
                'bank_detected': 'Unknown',
            }
            if debug and debug_log is not None:
                debug_log.append(f"Exception occurred: {e}")
                result['debug_log'] = debug_log
            return result

    def _extract_text_from_pdf(self, file_path: str, debug_log: Optional[List[str]] = None) -> str:
        """
        Extract text content from PDF file using multiple methods.

        Args:
            file_path (str): Path to the PDF file.
            debug_log (Optional[List[str]]): List to append debug messages to.

        Returns:
            str: Cleaned extracted text.
        """
        text_content = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
            if debug_log is not None:
                debug_log.append("pdfplumber succeeded")
        except Exception as e:
            self.logger.warning(f"pdfplumber failed: {e}")
            if debug_log is not None:
                debug_log.append(f"pdfplumber failed: {e}")

        # Fallback a PyPDF2 si pdfplumber no extrajo texto
        if not text_content.strip():
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"
                if debug_log is not None:
                    debug_log.append("PyPDF2 succeeded")
            except Exception as e:
                self.logger.warning(f"PyPDF2 failed: {e}")
                if debug_log is not None:
                    debug_log.append(f"PyPDF2 failed: {e}")

        return clean_text(text_content)

    def _detect_bank(self, text_content: str) -> str:
        """
        Detect the bank based on text content patterns.

        Args:
            text_content (str): Extracted text from PDF

        Returns:
            str: Bank identifier string
        """
        text_lower = text_content.lower()
        # (resto de detectores de banco...)
        return 'unknown'

    def _validate_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean transaction data.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            List[Dict[str, Any]]: List of validated transactions
        """
        valid_transactions: List[Dict[str, Any]] = []
        for transaction in transactions:
            if not all(key in transaction for key in ['date', 'description', 'amount']):
                continue
            if not self._is_valid_date(transaction.get('date')):
                continue
            try:
                amount = parse_amount(transaction.get('amount', '0'))
                transaction['amount'] = amount
            except (ValueError, TypeError):
                continue
            transaction['description'] = clean_text(transaction.get('description', ''))
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
