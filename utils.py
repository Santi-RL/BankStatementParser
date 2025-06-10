import re
import locale
from typing import Optional, List, Any
from datetime import datetime
import logging

def clean_text(text: str, preserve_lines: bool = False) -> str:
    """Clean and normalize text content.

    Parameters
    ----------
    text: str
        Raw text to clean.
    preserve_lines: bool, optional
        When ``True`` line breaks are kept so the caller can split the text
        into lines. The default ``False`` mimics the previous behaviour of
        collapsing all whitespace.

    Returns
    -------
    str
        Normalised text string.
    """

    if not text:
        return ""

    if preserve_lines:
        # Normalise CR/LF pairs and remove unwanted characters while
        # preserving ``\n`` for line splitting.
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'[^\w\s\-.,/()áéíóúüñÁÉÍÓÚÜÑ€$£¥]', ' ', text)
        # Collapse spaces and tabs but keep newlines
        text = re.sub(r'[ \t]+', ' ', text)
        # Collapse multiple blank lines
        text = re.sub(r'\n{2,}', '\n', text)
        # Trim whitespace around each line
        text = '\n'.join(line.strip() for line in text.split('\n'))
        return text.strip()

    # Previous behaviour: replace all whitespace with a single space
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[^\w\s\-.,/()áéíóúüñÁÉÍÓÚÜÑ€$£¥]', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def parse_amount(amount_str: str) -> float:
    """
    Parse monetary amount from string, handling different formats.
    
    Args:
        amount_str: String representation of amount
        
    Returns:
        Parsed amount as float
        
    Raises:
        ValueError: If amount cannot be parsed
    """
    if not amount_str:
        return 0.0
    
    # Convert to string and clean
    amount_str = str(amount_str).strip()
    
    # Remove currency symbols
    amount_str = re.sub(r'[€$£¥]', '', amount_str)
    
    # Handle negative amounts in parentheses
    if amount_str.startswith('(') and amount_str.endswith(')'):
        amount_str = '-' + amount_str[1:-1]
    
    # Handle Spanish/European format (1.234,56)
    if re.match(r'^[-+]?\d{1,3}(?:\.\d{3})*,\d{2}$', amount_str):
        # Remove thousand separators (dots) and replace comma with dot
        amount_str = amount_str.replace('.', '').replace(',', '.')
    
    # Handle US format (1,234.56)
    elif re.match(r'^[-+]?\d{1,3}(?:,\d{3})*\.\d{2}$', amount_str):
        # Remove thousand separators (commas)
        amount_str = amount_str.replace(',', '')
    
    # Handle simple formats
    else:
        # Replace comma with dot for decimal separator
        amount_str = amount_str.replace(',', '.')
        # Remove any remaining non-numeric characters except dot and minus
        amount_str = re.sub(r'[^\d.\-+]', '', amount_str)
    
    try:
        return float(amount_str)
    except ValueError:
        raise ValueError(f"Cannot parse amount: {amount_str}")

def parse_date(date_str: str) -> Optional[str]:
    """
    Parse date string into standardized format.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Standardized date string (YYYY-MM-DD) or None if parsing fails
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Common date formats
    formats = [
        '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
        '%d/%m/%y', '%d-%m-%y', '%y-%m-%d',
        '%d.%m.%Y', '%d.%m.%y',
        '%m/%d/%Y', '%m-%d-%Y',
        '%d %m %Y', '%d %m %y'
    ]
    
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            # Convert 2-digit years
            if parsed_date.year < 50:
                parsed_date = parsed_date.replace(year=parsed_date.year + 2000)
            elif parsed_date.year < 100:
                parsed_date = parsed_date.replace(year=parsed_date.year + 1900)
            
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None

def format_currency(amount: float, currency: str = 'EUR') -> str:
    """
    Format currency amount for display.
    
    Args:
        amount: Numeric amount
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    if currency == 'EUR':
        return f"{amount:,.2f} €"
    elif currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'GBP':
        return f"£{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"

def validate_pdf_files(uploaded_files: List[Any]) -> dict:
    """
    Validate uploaded PDF files.
    
    Args:
        uploaded_files: List of uploaded file objects
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    max_files = 10
    max_size_mb = 50
    
    # Check number of files
    if len(uploaded_files) > max_files:
        errors.append(f"Too many files uploaded. Maximum allowed: {max_files}")
    
    # Check each file
    for file in uploaded_files:
        # Check file type
        if not file.name.lower().endswith('.pdf'):
            errors.append(f"Invalid file type for {file.name}. Only PDF files are allowed.")
            continue
        
        # Check file size
        file_size_mb = len(file.getvalue()) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            errors.append(f"File {file.name} is too large ({file_size_mb:.1f}MB). Maximum allowed: {max_size_mb}MB")
        
        # Reset file pointer after reading
        file.seek(0)
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def get_transaction_category(description: str) -> str:
    """
    Categorize transaction based on description.
    
    Args:
        description: Transaction description
        
    Returns:
        Category string
    """
    description_lower = description.lower()
    
    # Food and dining
    if any(keyword in description_lower for keyword in [
        'restaurante', 'restaurant', 'cafe', 'bar', 'comida', 'food',
        'mercadona', 'carrefour', 'supermercado', 'grocery', 'market'
    ]):
        return 'Food & Dining'
    
    # Transportation
    elif any(keyword in description_lower for keyword in [
        'gasolina', 'gas', 'taxi', 'uber', 'metro', 'bus', 'train',
        'parking', 'aparcamiento', 'peaje', 'toll'
    ]):
        return 'Transportation'
    
    # Shopping
    elif any(keyword in description_lower for keyword in [
        'amazon', 'ebay', 'tienda', 'shop', 'store', 'compra', 'purchase',
        'zara', 'h&m', 'corte ingles'
    ]):
        return 'Shopping'
    
    # Bills and utilities
    elif any(keyword in description_lower for keyword in [
        'luz', 'agua', 'gas', 'telefono', 'internet', 'electric', 'water',
        'phone', 'utility', 'bill', 'factura', 'recibo'
    ]):
        return 'Bills & Utilities'
    
    # Banking
    elif any(keyword in description_lower for keyword in [
        'comision', 'fee', 'interes', 'interest', 'transferencia', 'transfer',
        'cajero', 'atm', 'banco', 'bank'
    ]):
        return 'Banking & Fees'
    
    # Income
    elif any(keyword in description_lower for keyword in [
        'nomina', 'salary', 'sueldo', 'pago', 'payment', 'ingreso', 'income'
    ]):
        return 'Income'
    
    # Healthcare
    elif any(keyword in description_lower for keyword in [
        'farmacia', 'pharmacy', 'medico', 'doctor', 'hospital', 'clinic',
        'seguro', 'insurance', 'salud', 'health'
    ]):
        return 'Healthcare'
    
    else:
        return 'Other'

def extract_account_number(text: str) -> Optional[str]:
    """
    Extract account number from text using common patterns.
    
    Args:
        text: Text content to search
        
    Returns:
        Account number if found, None otherwise
    """
    patterns = [
        r'IBAN[:\s]+([A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}[A-Z0-9]{1,3})',
        r'N[úu]mero de cuenta[:\s]+([0-9\-\s]{10,30})',
        r'Account number[:\s]+([0-9\-\s]{8,20})',
        r'Cuenta[:\s]+([0-9\-\s]{8,20})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().replace(' ', '').replace('-', '')
    
    return None
