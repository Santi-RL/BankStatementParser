import pytest
from parsers.argentina.base import ArgentinianBankParser

sample_text = "05/05/2025 Compra en tienda -1000,00 5000,00"

def test_argentinian_default_currency_and_date():
    parser = ArgentinianBankParser()
    txs = parser.parse_transactions(sample_text, "test.pdf")
    assert len(txs) == 1
    assert txs[0]['date'] == '2025-05-05'
    assert txs[0]['currency'] == 'ARS'
