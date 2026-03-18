import io
from pathlib import Path

import pytest
from openpyxl import load_workbook

import pdf_processor as pdf_processor_module
from app import _display_total_amount
from excel_generator import ExcelGenerator
from pdf_processor import PDFProcessor
from utils import temporary_pdf_copy


def _build_summary(total_transactions: int, selected_scopes: list[dict] | None = None) -> dict:
    return {
        "total_files": 1,
        "successful_files": 1,
        "failed_files": 0,
        "total_transactions": total_transactions,
        "banks_detected": {"bbva"},
        "errors": [],
        "selected_scopes": selected_scopes or [],
    }


def _find_summary_value(workbook, label: str):
    worksheet = workbook["Summary"]
    for row in worksheet.iter_rows(min_col=1, max_col=2):
        if row[0].value == label:
            return row[1].value
    raise AssertionError(f"Label not found in Summary sheet: {label}")


class CountingProcessor(PDFProcessor):
    def __init__(self, text: str):
        super().__init__()
        self._text = text
        self.extract_calls = 0

    def _extract_text_from_pdf(self, file_path, debug_log=None):
        self.extract_calls += 1
        if debug_log is not None:
            debug_log.append("counting extractor")
        return self._text


def test_process_pdf_reuses_single_text_extraction():
    text = Path("parser_specs/galicia_ar/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    processor = CountingProcessor(text)

    result = processor.process_pdf("dummy.pdf", "dummy.pdf", debug=True)

    assert result["success"] is True
    assert processor.extract_calls == 1
    assert "counting extractor" in result["debug_log"]


def test_extract_text_falls_back_to_pypdf(monkeypatch, tmp_path):
    pdf_path = tmp_path / "fallback.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fallback")

    class DummyPage:
        def extract_text(self):
            return "Fallback text from pypdf"

    class DummyReader:
        def __init__(self, file_obj):
            self.pages = [DummyPage()]

    processor = PDFProcessor()
    debug_log: list[str] = []

    monkeypatch.setattr(pdf_processor_module, "pdfplumber", None)
    monkeypatch.setattr(pdf_processor_module, "PdfReader", DummyReader)

    extracted_text = processor._extract_text_from_pdf(str(pdf_path), debug_log)

    assert "Fallback text from pypdf" in extracted_text
    assert "pypdf succeeded" in debug_log


def test_temporary_pdf_copy_cleans_up_after_exception():
    temp_path: Path | None = None

    with pytest.raises(RuntimeError):
        with temporary_pdf_copy(b"%PDF-1.4 test payload") as generated_path:
            temp_path = Path(generated_path)
            assert temp_path.exists()
            raise RuntimeError("boom")

    assert temp_path is not None
    assert not temp_path.exists()


def test_display_total_amount_uses_transaction_currency():
    transactions = [
        {"amount": 100.0, "currency": "ARS"},
        {"amount": -40.0, "currency": "ARS"},
    ]

    assert _display_total_amount(transactions) == "AR$60.00"


def test_display_total_amount_flags_multiple_currencies():
    transactions = [
        {"amount": 100.0, "currency": "ARS"},
        {"amount": -40.0, "currency": "USD"},
    ]

    assert _display_total_amount(transactions) == "N/A (múltiples monedas)"


def test_excel_scope_sheet_titles_are_sanitized_and_deduplicated():
    transactions = [
        {
            "date": "2024-01-01",
            "description": "Ingreso",
            "amount": 10.0,
            "balance": 10.0,
            "transaction_type": "Credit",
            "bank": "bbva",
            "account": "1",
            "currency": "EUR",
            "scope_label": "Cuenta / Uno",
            "product_type": "bank_account",
            "linked_account": "",
            "source_file": "bbva.pdf",
        },
        {
            "date": "2024-01-02",
            "description": "Debito",
            "amount": -5.0,
            "balance": 5.0,
            "transaction_type": "Debit",
            "bank": "bbva",
            "account": "2",
            "currency": "EUR",
            "scope_label": "Cuenta : Uno",
            "product_type": "bank_account",
            "linked_account": "",
            "source_file": "bbva.pdf",
        },
    ]

    workbook_bytes = ExcelGenerator().create_excel_file(transactions, _build_summary(total_transactions=2))
    workbook = load_workbook(io.BytesIO(workbook_bytes))

    assert "bbva Cuenta Uno" in workbook.sheetnames
    assert "bbva Cuenta Uno 2" in workbook.sheetnames
    assert all(all(character not in name for character in r'[]:*?/\\') for name in workbook.sheetnames)


def test_excel_summary_flags_multiple_currencies():
    transactions = [
        {
            "date": "2024-01-01",
            "description": "Ingreso",
            "amount": 10.0,
            "balance": 10.0,
            "transaction_type": "Credit",
            "bank": "bbva",
            "account": "1",
            "currency": "EUR",
        },
        {
            "date": "2024-01-02",
            "description": "Debito",
            "amount": -5.0,
            "balance": 5.0,
            "transaction_type": "Debit",
            "bank": "bbva",
            "account": "1",
            "currency": "USD",
        },
    ]

    workbook_bytes = ExcelGenerator().create_excel_file(transactions, _build_summary(total_transactions=2))
    workbook = load_workbook(io.BytesIO(workbook_bytes))

    assert _find_summary_value(workbook, "Total Credits:") == "N/A (multiple currencies)"
    assert _find_summary_value(workbook, "Total Debits:") == "N/A (multiple currencies)"
    assert _find_summary_value(workbook, "Net Amount:") == "N/A (multiple currencies)"
