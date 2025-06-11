import pytest
from parsers.argentina.base import ArgentinianBankParser

sample_text = "05/05/2025 Compra en tienda -1000,00 5000,00"
sample_text_usd = "Cuenta en USD\n05/05/2025 Compra en tienda -1000,00 5000,00"
sample_text_peso = "Caja de Ahorro en Pesos $172.096,76\n05/05/2025 Compra en tienda -1000,00 5000,00"

def test_argentinian_default_currency_and_date():
    parser = ArgentinianBankParser()
    txs = parser.parse_transactions(sample_text, "test.pdf")
    assert len(txs) == 1
    assert txs[0]['date'] == '2025-05-05'
    assert txs[0]['currency'] == 'ARS'


def test_argentinian_usd_detection():
    parser = ArgentinianBankParser()
    txs = parser.parse_transactions(sample_text_usd, "test.pdf")
    assert len(txs) == 1
    assert txs[0]['currency'] == 'USD'


def test_argentinian_peso_detection_with_dollar_sign():
    parser = ArgentinianBankParser()
    txs = parser.parse_transactions(sample_text_peso, "test.pdf")
    assert len(txs) == 1
    assert txs[0]['currency'] == 'ARS'
