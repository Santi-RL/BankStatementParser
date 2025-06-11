import pytest
from parsers.argentina.galicia import GaliciaParser
from pdf_processor import PDFProcessor

sample_text = "\n".join([
    "Cuenta en PESO",
    "05/05/25 DEB. AUTOM. DE SERV. -48.829,05 123.267,71",
    "05/05/25 TRANSFERENCIA DE CUENTA 100.000,00 223.267,71",
])

sample_text_multiline = "\n".join([
    "05/05/25 DEB. AUTOM. DE SERV. -48.829,05 123.267,71",
    "ANSES RES 193 23",
    "NORMAL",
    "0001092143_015",
    "23318277559",
    "05/05/25 TRANSFERENCIA DE CUENTA 100.000,00 223.267,71",
    "PROPIA",
    "ROJAS/LEM SANTIAGO L",
    "23318277559",
    "01703311400000492384",
    "3310004923847",
    "4517650653303578",
    "VARIOS",
    "05/05/25 DEB. AUTOM. DE SERV. -166.046,59 57.221,12",
    "OMINT SA",
    "CUOTAS 1",
    "FAC 5006276065",
    "19729417",
])

def test_detect_bank_galicia():
    processor = PDFProcessor()
    assert processor._detect_bank("Banco de Galicia y Buenos Aires S.A.U.") == 'galicia_ar'

def test_galicia_parser():
    parser = GaliciaParser()
    txs = parser.parse_transactions(sample_text, "test.pdf")
    assert len(txs) == 2
    assert txs[0]['date'] == '2025-05-05'
    assert txs[0]['amount'] == -48829.05
    assert txs[1]['amount'] == 100000.00
    assert all(t['currency'] == 'ARS' for t in txs)


def test_galicia_multiline_description():
    parser = GaliciaParser()
    txs = parser.parse_transactions(sample_text_multiline, "test.pdf")
    assert len(txs) == 3
    assert "ANSES RES 193 23 NORMAL 0001092143_015 23318277559" in txs[0]['description']
