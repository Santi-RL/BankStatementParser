import pytest
from parsers.argentina.roela_ar import RoelaParser


def test_roela_parser():
    parser = RoelaParser()
    with open("attached_assets/TestBancoRoelaArg.txt", "r") as f:
        sample_text = f.read()
    txs = parser.parse_transactions(sample_text, "test.pdf")
    assert len(txs) >= 5
    assert all(t["currency"] == "ARS" for t in txs)


def test_roela_parser_pdf_order():
    parser = RoelaParser()
    with open("attached_assets/TestBancoRoelaArg.txt", "r") as f:
        sample_text = f.read()

    txs_text = parser.parse_transactions(sample_text, "dummy.pdf")
    txs_pdf = parser.parse_transactions("", "attached_assets/BancoRoela.Argentina.Test.pdf")

    pdf_desc = [t["description"] for t in txs_pdf]
    target_desc = [t["description"] for t in txs_text[:5]]

    pos = 0
    for desc in target_desc:
        while pos < len(pdf_desc) and pdf_desc[pos] != desc:
            pos += 1
        assert pos < len(pdf_desc)
        pos += 1
