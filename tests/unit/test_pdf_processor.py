from pdf_processor import DETECTION_HEADER_MAX_LINES, PDFProcessor
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


def test_detect_bank_mercado_pago():
    processor = PDFProcessor()
    text = "Resumen de cuenta Mercado Pago con CVU 0000003100043499119011 y mercadopago.com.ar"
    assert processor._detect_bank(text) == "mercado_pago"


def test_detect_bank_mercado_pago_is_not_confused_by_bbva_in_transaction_detail():
    processor = PDFProcessor()
    text = Path("parser_specs/mercado_pago/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    contaminated_text = "\n".join(
        [
            text,
            "07-06-2023 Ingreso de dinero Cuenta BBVA Banco Frances 59084863410 3.000,00 7.448,16",
        ]
    )
    assert processor._detect_bank(contaminated_text) == "mercado_pago"


def test_detect_bank_weighted_keyword_requires_header_signal():
    processor = PDFProcessor()
    text = "\n".join(
        [f"Línea de resumen {line_number}" for line_number in range(1, DETECTION_HEADER_MAX_LINES + 1)]
        + [
            "07-06-2023 Ingreso de dinero Cuenta BBVA Banco Frances 59084863410 3.000,00 7.448,16",
            "Tarjetas de Crédito",
        ]
    )
    assert processor._detect_bank(text) == "unknown"


def test_detect_bank_simple_keyword_requires_header_signal():
    processor = PDFProcessor()
    text = "\n".join(
        [f"Línea de resumen {line_number}" for line_number in range(1, DETECTION_HEADER_MAX_LINES + 1)]
        + [
            "07/06/2023 Transferencia enviada a cuenta Santander 100,00",
        ]
    )
    assert processor._detect_bank(text) == "unknown"


def test_detect_bank_simple_keyword_requires_header_signal_even_with_short_header():
    processor = PDFProcessor()
    text = "\n".join(
        [
            "Resumen de cuenta",
            "Saldo inicial",
            "Movimientos del período",
            "07/06/2023 Transferencia enviada a cuenta Santander 100,00",
        ]
    )
    assert processor._detect_bank(text) == "unknown"


def test_detect_bank_simple_keyword_in_header_is_still_detected():
    processor = PDFProcessor()
    text = "\n".join(
        [
            "Banco Santander",
            "Resumen de cuenta",
            "Saldo y movimientos",
        ]
    )
    assert processor._detect_bank(text) == "santander"


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


def test_bbva_account_summary_with_four_valid_transactions_is_not_rejected_as_format_changed():
    text = "\n".join(
        [
            "110243804202310261DIGITAL",
            "Resumen",
            "Cuentas y paquetes",
            "PERSONA",
            "Cuentas",
            "CONSOLIDADO",
            "CA $ 354-428727/2 (Caja de Ahorros) Saldo Consolidado",
            "CBU 01703540 40000042872724 Sucursal gestora 0354 $ 0,00",
            "Intervinientes",
            "PERSONA",
            "DETALLE",
            "Movimientos en cuentas",
            "CA $ 354-428727/2 (Caja de Ahorros) - A Consumidor Final",
            "FECHA ORIGEN CONCEPTO DÉBITO CRÉDITO SALDO",
            "SALDO ANTERIOR 0,00",
            "17/10 MOVIM. ENTRE CUENTAS CCP354 560404 1 144.645,66 144.645,66",
            "17/10 CUENTA VISA NRO. XXXXXXXXXXXXXX -144.645,66 0,00",
            "17/10 MOVIM. ENTRE CUENTAS CCP354 560404 1 2.572,98 2.572,98",
            "17/10 CUENTA VISA NRO. XXXXXXXXXXXXXX -2.572,98 0,00",
            "SALDO AL 26 DE OCTUBRE 0,00",
            "TOTAL MOVIMIENTOS -147.218,64 147.218,64",
            "Legales y avisos",
        ]
    )
    proc = DummyProcessor(text)

    analysis = proc.analyze_pdf("dummy.pdf", "Resumen caja de ahorro BBVA 10-2023.pdf")
    result = proc.process_pdf("dummy.pdf", "Resumen caja de ahorro BBVA 10-2023.pdf")

    assert analysis["success"] is True
    assert analysis["format_id"] == "account_summary"
    assert analysis["parse_status"] == "ok"
    assert len(analysis["available_scopes"]) == 1

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["format_id"] == "account_summary"
    assert result["total_transactions"] == 4
    assert result["transactions"][0]["amount"] == 144645.66
    assert result["transactions"][-1]["amount"] == -2572.98


def test_list_available_formats_returns_published_specs():
    processor = PDFProcessor()
    formats = processor.list_available_formats()
    assert len(formats) > 0
    for fmt in formats:
        assert "bank_id" in fmt
        assert "format_id" in fmt
        assert "display_name" in fmt
        assert "label" in fmt
    bank_ids = [fmt["bank_id"] for fmt in formats]
    assert "galicia_ar" in bank_ids
    assert "chase" in bank_ids


def test_process_pdf_with_format_override_bypasses_detection():
    """When override is provided, the specified format is used even when auto-detection fails."""
    text = Path("parser_specs/galicia_ar/default/fixtures/sample_text.txt").read_text(encoding="utf-8")

    # Build a long header of unrelated lines so that no published spec matches
    # (galicia required_keywords are not present in these lines).
    _NOISE_LINE_COUNT = 200
    noisy_text = "\n".join(f"Línea de ruido {n}" for n in range(1, _NOISE_LINE_COUNT + 1))

    # Without override: fails because no spec matches
    proc_noise = DummyProcessor(noisy_text)
    result_no_override = proc_noise.process_pdf("dummy.pdf", "dummy.pdf")
    assert result_no_override["success"] is False
    assert result_no_override["parse_status"] == "unknown_format"

    # With the galicia text and override pointing to galicia: succeeds
    proc_galicia = DummyProcessor(text)
    result_override = proc_galicia.process_pdf(
        "dummy.pdf", "dummy.pdf",
        override_bank_id="galicia_ar",
        override_format_id="default",
    )
    assert result_override["success"] is True
    assert result_override["bank_detected"] == "galicia_ar"
    assert result_override["format_id"] == "default"


def test_process_pdf_with_invalid_override_returns_unmatched():
    """When override points to a non-existent spec, processing fails gracefully."""
    text = Path("parser_specs/galicia_ar/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    proc = DummyProcessor(text)

    result = proc.process_pdf(
        "dummy.pdf", "dummy.pdf",
        override_bank_id="nonexistent_bank",
        override_format_id="default",
    )
    assert result["success"] is False
    assert result["parse_status"] == "unknown_format"
