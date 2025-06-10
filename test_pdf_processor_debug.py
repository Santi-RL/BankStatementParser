import sys
import types
import pytest

# Provide dummy modules so pdf_processor can be imported without real dependencies
sys.modules.setdefault('pdfplumber', types.ModuleType('pdfplumber'))
sys.modules.setdefault('PyPDF2', types.ModuleType('PyPDF2'))

from pdf_processor import PDFProcessor


def test_process_pdf_debug(monkeypatch):
    sample_text = "Bank of America\n01/01/2024 Coffee Shop $5.00 $1000.00"

    def mock_extract(self, file_path):
        return sample_text

    monkeypatch.setattr(PDFProcessor, "_extract_text_from_pdf", mock_extract)

    processor = PDFProcessor()
    result = processor.process_pdf("dummy.pdf", "dummy.pdf", debug=True)

    assert result["success"] is True
    assert "steps" in result
    steps = result["steps"]
    assert any(step.startswith("bank_detected:") for step in steps)
    assert any(step.startswith("transactions_parsed:") for step in steps)
    assert any(step.startswith("transactions_validated:") for step in steps)
