from pdf_processor import PDFProcessor
from pathlib import Path


class DummyProcessor(PDFProcessor):
    def __init__(self, text: str):
        super().__init__()
        self._text = text

    def _extract_text_from_pdf(self, file_path, debug_log=None):
        if debug_log is not None:
            debug_log.append("dummy extractor")
        return self._text


def test_detect_bank_chase():
    processor = PDFProcessor()
    assert processor._detect_bank("This is a statement from JPMorgan Chase Bank.") == "chase"


def test_process_pdf_debug():
    text = Path("parser_specs/galicia_ar/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    proc = DummyProcessor(text)

    result = proc.process_pdf("dummy.pdf", "dummy.pdf", debug=True)

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert "debug_log" in result
    assert "dummy extractor" in result["debug_log"]


def test_declared_format_change_is_reported():
    changed_text = "\n".join(
        [
            "Resumen de Caja de Ahorro en Pesos",
            "Movimientos",
            "Fecha Descripción Origen Crédito Débito Saldo",
            "2025-05-05 Formato nuevo sin balance 1.000,00",
            "Banco de Galicia y Buenos Aires S.A.U.",
        ]
    )
    processor = DummyProcessor(changed_text)
    result = processor.process_pdf("dummy.pdf", "dummy.pdf")

    assert result["success"] is False
    assert result["parse_status"] == "format_changed"
    assert result["bank_detected"] == "galicia_ar"


def test_unknown_format_is_reported():
    processor = DummyProcessor("Completely unknown statement layout without known bank markers")
    result = processor.process_pdf("dummy.pdf", "dummy.pdf")

    assert result["success"] is False
    assert result["parse_status"] == "unknown_format"


def test_detected_bank_without_published_spec_is_unknown_format():
    processor = DummyProcessor("Banco Santander resumen de cuenta con saldo y movimientos")
    result = processor.process_pdf("dummy.pdf", "dummy.pdf")

    assert result["success"] is False
    assert result["parse_status"] == "unknown_format"
    assert result["bank_detected"] == "santander"


def test_multi_scope_document_requires_selection_before_processing():
    text = Path("parser_specs/bbva/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    proc = DummyProcessor(text)

    analysis = proc.analyze_pdf("dummy.pdf", "dummy.pdf")
    result = proc.process_pdf("dummy.pdf", "dummy.pdf")

    assert analysis["success"] is True
    assert analysis["multi_scope"] is True
    assert len(analysis["available_scopes"]) == 5
    assert result["success"] is False
    assert result["parse_status"] == "validation_failed"
