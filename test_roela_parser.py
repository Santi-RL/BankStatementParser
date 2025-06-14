import pytest
from parsers.argentina.roela_ar import RoelaParser


def test_roela_parser():
    parser = RoelaParser()
    with open("attached_assets/TestBancoRoelaArg.txt", "r") as f:
        sample_text = f.read()
    txs = parser.parse_transactions(sample_text, "test.pdf")
    assert len(txs) >= 5
    assert all(t["currency"] == "ARS" for t in txs)
