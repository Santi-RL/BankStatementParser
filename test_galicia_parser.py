import pytest
from parsers.argentina.galicia import GaliciaParser
from pdf_processor import PDFProcessor

sample_text = "\n".join([
    "Cuenta en PESO",
    "05/05/25 DEB. AUTOM. DE SERV. -48.829,05 123.267,71",
    "05/05/25 TRANSFERENCIA DE CUENTA 100.000,00 223.267,71",
])

def test_detect_bank_galicia():
    processor = PDFProcessor()
    assert processor._detect_bank("Banco de Galicia y Buenos Aires S.A.U.") == 'galicia'

def test_galicia_parser():
    parser = GaliciaParser()
    txs = parser.parse_transactions(sample_text, "test.pdf")
    assert len(txs) == 2
    assert txs[0]['date'] == '2025-05-05'
    assert txs[0]['amount'] == -48829.05
    assert txs[1]['amount'] == 100000.00
    assert all(t['currency'] == 'ARS' for t in txs)
