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


class ForcedDetectionProcessor(DummyProcessor):
    def __init__(self, text: str, detected_bank: str = "unknown"):
        super().__init__(text)
        self._detected_bank = detected_bank

    def _detect_bank(self, text_content: str) -> str:
        return self._detected_bank


def test_detect_bank_chase():
    processor = PDFProcessor()
    assert processor._detect_bank("This is a statement from JPMorgan Chase Bank.") == "chase"


def test_detect_bank_mercado_pago():
    processor = PDFProcessor()
    text = "Resumen de cuenta Mercado Pago con CVU 0000003100043499119011 y mercadopago.com.ar"
    assert processor._detect_bank(text) == "mercado_pago"


def test_detect_bank_brubank_via_published_spec():
    processor = PDFProcessor()
    text = Path("parser_specs/brubank/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    assert processor._detect_bank(text) == "brubank"


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


def test_galicia_single_transaction_statement_is_accepted_and_ignores_totals():
    text = "\n".join(
        [
            "Resumen de Caja de Ahorro en Pesos",
            "Datos de la cuenta",
            "Número de cuenta",
            "N 4046017-6 335-0",
            "Movimientos",
            "Fecha Descripción Origen Crédito Débito Saldo",
            "25/08/23 TRANSFERENCIA DE CUENTA 100.000,00 100.000,00",
            "PROPIA",
            "PROZZI/ANDRES LEONEL",
            "20332862368",
            "CUENTA ORIGEN CTA CT",
            "3540005604041",
            "4517650664260429",
            "VARIOS",
            "Total $ 100.000,00 -$ 0,00 $ 100.000,00",
            "Los depósitos en pesos y en moneda extranjera cuentan con la garantía de hasta $ 1.500.000.",
        ]
    )
    processor = DummyProcessor(text)

    result = processor.process_pdf("dummy.pdf", "dummy.pdf")

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["bank_detected"] == "galicia_ar"
    assert result["total_transactions"] == 1
    assert "Total $" not in result["transactions"][0]["description"]
    assert result["transactions"][0]["amount"] == 100000.0
    assert result["transactions"][0]["balance"] == 100000.0


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


def test_list_available_formats_returns_only_published_specs():
    processor = PDFProcessor()

    formats = processor.list_available_formats()

    assert formats
    assert all("bank_id" in fmt and "format_id" in fmt and "label" in fmt for fmt in formats)
    assert any(fmt["bank_id"] == "galicia_ar" and fmt["format_id"] == "default" for fmt in formats)
    assert any(fmt["bank_id"] == "bbva" and fmt["format_id"] == "account_summary" for fmt in formats)


def test_analyze_pdf_with_override_can_surface_multiscope_options():
    text = Path("parser_specs/bbva/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    processor = ForcedDetectionProcessor(text, detected_bank="unknown")

    analysis = processor.analyze_pdf(
        "dummy.pdf",
        "dummy.pdf",
        override_bank_id="bbva",
        override_format_id="default",
    )

    assert analysis["success"] is True
    assert analysis["bank_detected"] == "bbva"
    assert analysis["format_id"] == "default"
    assert analysis["multi_scope"] is True
    assert len(analysis["available_scopes"]) == 5


def test_process_pdf_with_override_bypasses_wrong_bank_detection():
    text = Path("parser_specs/galicia_ar/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    processor = ForcedDetectionProcessor(text, detected_bank="santander")

    without_override = processor.process_pdf("dummy.pdf", "dummy.pdf")
    with_override = processor.process_pdf(
        "dummy.pdf",
        "dummy.pdf",
        override_bank_id="galicia_ar",
        override_format_id="default",
    )

    assert without_override["success"] is False
    assert without_override["parse_status"] == "unknown_format"
    assert with_override["success"] is True
    assert with_override["bank_detected"] == "galicia_ar"
    assert with_override["format_id"] == "default"


def test_process_pdf_with_override_keeps_scope_selection_flow():
    text = Path("parser_specs/bbva/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    processor = ForcedDetectionProcessor(text, detected_bank="unknown")
    analysis = processor.analyze_pdf(
        "dummy.pdf",
        "dummy.pdf",
        override_bank_id="bbva",
        override_format_id="default",
    )
    selected_scope_id = analysis["available_scopes"][0]["id"]

    result = processor.process_pdf(
        "dummy.pdf",
        "dummy.pdf",
        selected_scope_ids=[selected_scope_id],
        override_bank_id="bbva",
        override_format_id="default",
    )

    assert result["success"] is True
    assert result["multi_scope"] is True
    assert result["transactions"]
    assert {transaction["scope_id"] for transaction in result["transactions"]} == {selected_scope_id}


def test_process_pdf_with_invalid_override_returns_unknown_format():
    text = Path("parser_specs/galicia_ar/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    processor = ForcedDetectionProcessor(text, detected_bank="galicia_ar")

    result = processor.process_pdf(
        "dummy.pdf",
        "dummy.pdf",
        override_bank_id="galicia_ar",
        override_format_id="missing_format",
    )

    assert result["success"] is False
    assert result["parse_status"] == "unknown_format"
    assert result["diagnostics"]["override_missing"] is True


def test_brubank_fixture_processes_with_published_spec():
    text = Path("parser_specs/brubank/default/fixtures/sample_text.txt").read_text(encoding="utf-8")
    processor = DummyProcessor(text)

    analysis = processor.analyze_pdf("dummy.pdf", "brubank.pdf")
    result = processor.process_pdf("dummy.pdf", "brubank.pdf")

    assert analysis["success"] is True
    assert analysis["bank_detected"] == "brubank"
    assert analysis["format_id"] == "default"
    assert analysis["multi_scope"] is False

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["bank_detected"] == "brubank"
    assert result["format_id"] == "default"
    assert result["total_transactions"] == 34
    assert result["transactions"][0]["amount"] == -47000.0
    assert result["transactions"][-1]["amount"] == 24955.31


def test_brubank_multi_account_statement_requires_scope_selection_and_processes_all_selected():
    text = Path("parser_specs/brubank/default/fixtures/multi_account_sample_text.txt").read_text(encoding="utf-8")
    processor = DummyProcessor(text)

    analysis = processor.analyze_pdf("dummy.pdf", "brubank-multi.pdf")
    without_selection = processor.process_pdf("dummy.pdf", "brubank-multi.pdf")
    selected_scope_ids = [scope["id"] for scope in analysis["available_scopes"]]
    with_selection = processor.process_pdf(
        "dummy.pdf",
        "brubank-multi.pdf",
        selected_scope_ids=selected_scope_ids,
    )

    assert analysis["success"] is True
    assert analysis["bank_detected"] == "brubank"
    assert analysis["format_id"] == "default"
    assert analysis["multi_scope"] is True
    assert len(analysis["available_scopes"]) == 3
    assert {scope["currency"] for scope in analysis["available_scopes"]} == {"ARS", "USD"}

    assert without_selection["success"] is False
    assert without_selection["parse_status"] == "validation_failed"
    assert without_selection["multi_scope"] is True

    assert with_selection["success"] is True
    assert with_selection["parse_status"] == "ok"
    assert with_selection["total_transactions"] == 12
    assert {transaction["scope_label"] for transaction in with_selection["transactions"]} == {
        "Caja de ahorro ARS",
        "Cuenta remunerada ARS",
    }
