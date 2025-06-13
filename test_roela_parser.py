import pytest
from parsers.argentina.roela_ar import RoelaParser

sample_text = "\n".join([
    "02/09/2024 CREDITO 1.000,00",
    "03/09/2024 DEBITO -500,00",
    "SALDO AL 03/09/2024 500,00",
])


def test_roela_parser():
    parser = RoelaParser()
    txs = parser.parse_transactions(sample_text, "test.pdf")
    assert len(txs) == 2
    assert txs[0]['date'] == '2024-09-02'
    assert txs[0]['amount'] == 1000.00
    assert txs[1]['amount'] == -500.00
    assert all(t['currency'] == 'ARS' for t in txs)
