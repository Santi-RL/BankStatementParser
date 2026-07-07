import logging
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Optional


FORMULA_TRIGGER_CHARACTERS = ("=", "+", "-", "@", "\t", "\r", "\n")
TRANSACTION_PRESENTATION_COLUMN_ORDER = [
    "date",
    "description",
    "amount",
    "balance",
    "transaction_type",
    "bank",
    "account",
    "currency",
    "scope_label",
    "product_type",
    "linked_account",
    "source_file",
]
TRANSACTION_COLUMN_LABELS_ES = {
    "date": "Fecha",
    "description": "Descripción",
    "amount": "Monto",
    "balance": "Saldo",
    "transaction_type": "Tipo",
    "bank": "Banco",
    "account": "Cuenta",
    "currency": "Moneda",
    "scope_label": "Entidad",
    "product_type": "Tipo de producto",
    "linked_account": "Cuenta vinculada",
    "source_file": "Archivo de origen",
}
TRANSACTION_TYPE_LABELS_ES = {
    "Credit": "Crédito",
    "Debit": "Débito",
    "Neutral": "Neutral",
}
PRODUCT_TYPE_LABELS_ES = {
    "bank_account": "Cuenta bancaria",
    "credit_card": "Tarjeta de crédito",
    "debit_card": "Tarjeta de débito",
    "wallet_account": "Cuenta virtual",
}


def escape_spreadsheet_formula_value(value: Any) -> Any:
    """Escape text that spreadsheet apps could interpret as a formula."""

    if isinstance(value, str) and value.startswith(FORMULA_TRIGGER_CHARACTERS):
        return f"'{value}"
    return value


def user_facing_column_order(columns: Iterable[str]) -> List[str]:
    """Return known transaction columns first, preserving unknown columns after them."""

    available_columns = list(columns)
    ordered_columns = [column for column in TRANSACTION_PRESENTATION_COLUMN_ORDER if column in available_columns]
    ordered_columns.extend(column for column in available_columns if column not in ordered_columns)
    return ordered_columns


def user_facing_column_label(column: str) -> str:
    """Return the Spanish label for a transaction column shown to users."""

    return TRANSACTION_COLUMN_LABELS_ES.get(column, column)


def user_facing_transaction_type(value: Any) -> Any:
    """Return the Spanish label for internal transaction type values."""

    return TRANSACTION_TYPE_LABELS_ES.get(value, value)


def user_facing_product_type(value: Any) -> Any:
    """Return the Spanish label for internal product type values."""

    return PRODUCT_TYPE_LABELS_ES.get(value, value)


def user_facing_transaction_value(column: str, value: Any) -> Any:
    """Localize a transaction field value only for presentation/export surfaces."""

    if column == "transaction_type":
        return user_facing_transaction_type(value)
    if column == "product_type":
        return user_facing_product_type(value)
    return value


def user_facing_transaction_record(transaction: dict[str, Any]) -> dict[str, Any]:
    """Build a Spanish-labeled transaction record for UI, CSV, and spreadsheets."""

    return {
        user_facing_column_label(column): user_facing_transaction_value(column, transaction.get(column))
        for column in user_facing_column_order(transaction.keys())
    }


def user_facing_transaction_records(transactions: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """Build Spanish-labeled transaction records for UI, CSV, and spreadsheets."""

    return [user_facing_transaction_record(transaction) for transaction in transactions]

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
        text = re.sub(r'[^\w\s\-.,/()áéíóúüñÁÉÍÓÚÜÑ€$£¥!]', ' ', text)
        # Collapse spaces and tabs but keep newlines
        text = re.sub(r'[ \t]+', ' ', text)
        # Collapse multiple blank lines
        text = re.sub(r'\n{2,}', '\n', text)
        # Trim whitespace around each line
        text = '\n'.join(line.strip() for line in text.split('\n'))
        return text.strip()

    # Previous behaviour: replace all whitespace with a single space
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[^\w\s\-.,/()áéíóúüñÁÉÍÓÚÜÑ€$£¥!]', ' ', text)
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

def format_currency(amount: float, currency: Optional[str] = None) -> str:
    """
    Format currency amount for display.
    
    Args:
        amount: Numeric amount
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    normalized_currency = (currency or "").upper()

    if normalized_currency == 'EUR':
        return f"{amount:,.2f} €"
    elif normalized_currency == 'USD':
        return f"${amount:,.2f}"
    elif normalized_currency == 'GBP':
        return f"£{amount:,.2f}"
    elif normalized_currency == 'ARS':
        return f"AR${amount:,.2f}"
    elif normalized_currency:
        return f"{amount:,.2f} {normalized_currency}"
    return f"{amount:,.2f}"

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
        errors.append(f"Demasiados archivos cargados. Máximo permitido: {max_files}")
    
    # Check each file
    for file in uploaded_files:
        # Check file type
        if not file.name.lower().endswith('.pdf'):
            errors.append(f"Tipo de archivo inválido para {file.name}. Solo se permiten archivos PDF.")
            continue
        
        # Check file size
        file_size_mb = len(file.getvalue()) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            errors.append(
                f"El archivo {file.name} es demasiado grande ({file_size_mb:.1f}MB). "
                f"Máximo permitido: {max_size_mb}MB"
            )
        
        # Reset file pointer after reading
        file.seek(0)
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def get_transaction_currencies(transactions: List[dict[str, Any]]) -> List[str]:
    """Return the distinct non-empty currencies found in the transaction list."""

    currencies = {
        str(transaction.get("currency", "") or "").strip().upper()
        for transaction in transactions
        if str(transaction.get("currency", "") or "").strip()
    }
    return sorted(currencies)


def resolve_single_currency(transactions: List[dict[str, Any]]) -> Optional[str]:
    """Return the currency code only when all transactions share the same one."""

    currencies = get_transaction_currencies(transactions)
    if len(currencies) == 1:
        return currencies[0]
    return None


@contextmanager
def temporary_pdf_copy(payload: bytes, suffix: str = ".pdf") -> Iterator[str]:
    """Persist PDF bytes to a temporary path and ensure cleanup on exit."""

    temp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(payload)
            temp_path = tmp_file.name
        yield temp_path
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def setup_logging(mode: str = "local", debug: bool = False) -> logging.Logger:
    """Configure root logging for Streamlit and CLI entrypoints."""

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"

    level = logging.DEBUG if mode == "local" and debug else logging.INFO
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    root_logger.setLevel(level)
    root_logger.propagate = False

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    return root_logger


def set_logging_level(level: int) -> logging.Logger:
    """Update the root logger and all attached handlers to the same level."""

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)
    return root_logger


def get_supported_banks() -> List[str]:
    """Return a sorted list of published declarative formats currently supported."""

    from format_engine import FormatRegistry

    registry = FormatRegistry()
    return sorted({spec.display_name for spec in registry.specs_by_status("published")})
