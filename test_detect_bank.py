import pytest
from pdf_processor import PDFProcessor


def test_detect_bank_chase():
    processor = PDFProcessor()
    sample_text = "This is a statement from JPMorgan Chase Bank."
    assert processor._detect_bank(sample_text) == 'chase'
