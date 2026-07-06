from pathlib import Path

import tomllib

import pytest

from format_engine import FormatSpec
from format_training import regress_published_specs
from pdf_processor import PDFProcessor


class FixtureTextProcessor(PDFProcessor):
    def __init__(self, text: str):
        super().__init__()
        self._text = text

    def _extract_text_from_pdf(self, file_path, debug_log=None):
        if debug_log is not None:
            debug_log.append("fixture text extractor")
        return self._text


PARTIAL_TABLE_CHANGE_CASES = [
    {
        "id": "galicia_extra_amount_column",
        "bank_id": "galicia_ar",
        "format_id": "default",
        "spec_path": Path("parser_specs/galicia_ar/default/spec.toml"),
        "fixture_path": Path("tests/fixtures/format_changed_partial/galicia_extra_amount_column.txt"),
        "min_candidate_lines": 1,
    },
    {
        "id": "chase_trailing_status_column",
        "bank_id": "chase",
        "format_id": "default",
        "spec_path": Path("parser_specs/chase/default/spec.toml"),
        "fixture_path": Path("tests/fixtures/format_changed_partial/chase_trailing_status_column.txt"),
        "min_candidate_lines": 5,
    },
    {
        "id": "roela_trailing_currency_column",
        "bank_id": "roela_ar",
        "format_id": "default",
        "spec_path": Path("parser_specs/roela_ar/default/spec.toml"),
        "fixture_path": Path("tests/fixtures/format_changed_partial/roela_trailing_currency_column.txt"),
        "min_candidate_lines": 0,
    },
    {
        "id": "bbva_account_summary_extra_debit_credit_columns",
        "bank_id": "bbva",
        "format_id": "account_summary",
        "spec_path": Path("parser_specs/bbva/account_summary/spec.toml"),
        "fixture_path": Path("tests/fixtures/format_changed_partial/bbva_account_summary_extra_debit_credit_columns.txt"),
        "min_candidate_lines": 4,
    },
    {
        "id": "mercado_pago_extra_fee_column",
        "bank_id": "mercado_pago",
        "format_id": "default",
        "spec_path": Path("parser_specs/mercado_pago/default/spec.toml"),
        "fixture_path": Path("tests/fixtures/format_changed_partial/mercado_pago_extra_fee_column.txt"),
        "min_candidate_lines": 10,
    },
    {
        "id": "brubank_extra_amount_column",
        "bank_id": "brubank",
        "format_id": "default",
        "spec_path": Path("parser_specs/brubank/default/spec.toml"),
        "fixture_path": Path("tests/fixtures/format_changed_partial/brubank_extra_amount_column.txt"),
        "min_candidate_lines": 10,
    },
]


def _load_spec(path: Path) -> FormatSpec:
    with path.open("rb") as handle:
        return FormatSpec(path, tomllib.load(handle))


def _read_fixture(case):
    return case["fixture_path"].read_text(encoding="utf-8")



def test_published_spec_regression_suite_is_green():
    result = regress_published_specs()

    assert result["success"] is True
    assert result["processed"] >= 7


def test_changed_galicia_fixture_would_fail_spec_thresholds():
    spec_path = Path("parser_specs/galicia_ar/default/spec.toml")
    changed_text = "\n".join(
        [
            "Resumen de Caja de Ahorro en Pesos",
            "Movimientos",
            "Fecha Descripción Origen Crédito Débito Saldo",
            "2025-05-05 MOVIMIENTO NUEVO 10,00",
            "Banco de Galicia y Buenos Aires S.A.U.",
        ]
    )

    from format_engine import FormatSpec
    import tomllib

    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    result = spec.parse_transactions(changed_text)

    assert result.passes_change_detection is False
    assert result.diagnostics["transactions_found"] == 0


def test_changed_chase_fixture_would_fail_spec_thresholds():
    spec_path = Path("parser_specs/chase/default/spec.toml")
    changed_text = "\n".join(
        [
            "JPMorgan Chase Bank, N.A.",
            "DEPOSITS AND ADDITIONS",
            "ELECTRONIC WITHDRAWALS",
            "DATE DETAILS VALUE",
            "2024-01-02 Some New Layout $300.00",
            "Total Deposits and Additions $300.00",
        ]
    )

    from format_engine import FormatSpec
    import tomllib

    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    result = spec.parse_transactions(changed_text)

    assert result.passes_change_detection is False
    assert result.diagnostics["transactions_found"] == 0


def test_changed_roela_fixture_would_fail_spec_thresholds():
    spec_path = Path("parser_specs/roela_ar/default/spec.toml")
    changed_text = "\n".join(
        [
            "RESUMEN DE CUENTA CORRIENTE",
            "C.B.U. 2470001810000002253782",
            "Período Desde 01/09/2024",
            "02-09-2024 MOVIMIENTO NUEVO 11218.00",
            "DE INTERES PARA USTED",
        ]
    )

    from format_engine import FormatSpec
    import tomllib

    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    result = spec.parse_transactions(changed_text)

    assert result.passes_change_detection is False
    assert result.diagnostics["transactions_found"] == 0


def test_changed_bbva_account_summary_fixture_would_fail_spec_thresholds():
    spec_path = Path("parser_specs/bbva/account_summary/spec.toml")
    changed_text = "\n".join(
        [
            "110252400202309262DIGITAL",
            "Resumen",
            "Cuentas y paquetes",
            "Intervinientes",
            "Movimientos en cuentas",
            "FECHA ORIGEN CONCEPTO DÉBITO CRÉDITO SALDO",
            "2023-09-20 MOVIMIENTO NUEVO 10,00",
        ]
    )

    from format_engine import FormatSpec
    import tomllib

    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    result = spec.parse_transactions(changed_text)

    assert result.passes_change_detection is False
    assert result.diagnostics["transactions_found"] == 0


def test_changed_mercado_pago_fixture_would_fail_spec_thresholds():
    spec_path = Path("parser_specs/mercado_pago/default/spec.toml")
    changed_text = "\n".join(
        [
            "RESUMEN DE CUENTA",
            "CVU 0000003100000000000001 CUIT/ CUIL 20000000001",
            "DETALLE DE MOVIMIENTOS",
            "Fecha Descripción Valor Saldo",
            "2023/02/01 Movimiento nuevo 10,00 10,00",
        ]
    )

    from format_engine import FormatSpec
    import tomllib

    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    result = spec.parse_transactions(changed_text)

    assert result.passes_change_detection is False
    assert result.diagnostics["transactions_found"] == 0


def test_changed_brubank_fixture_would_fail_spec_thresholds():
    spec_path = Path("parser_specs/brubank/default/spec.toml")
    changed_text = "\n".join(
        [
            "Mi cuenta Resumen",
            "Movimientos",
            "Fecha Ref Descripción Débito Crédito Saldo",
            "2026/02/01 MOVIMIENTO NUEVO 10,00 10,00",
            "Brubank S.A.U.",
        ]
    )

    from format_engine import FormatSpec
    import tomllib

    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    result = spec.parse_transactions(changed_text)

    assert result.passes_change_detection is False
    assert result.diagnostics["transactions_found"] == 0

@pytest.mark.parametrize(
    "case",
    PARTIAL_TABLE_CHANGE_CASES,
    ids=[case["id"] for case in PARTIAL_TABLE_CHANGE_CASES],
)
def test_partial_table_change_fixtures_fail_spec_thresholds(case):
    spec = _load_spec(case["spec_path"])

    result = spec.parse_transactions(_read_fixture(case))

    assert result.passes_change_detection is False
    assert result.diagnostics["candidate_lines"] >= case["min_candidate_lines"]
    assert result.diagnostics["transactions_found"] == 0


@pytest.mark.parametrize(
    "case",
    PARTIAL_TABLE_CHANGE_CASES,
    ids=[case["id"] for case in PARTIAL_TABLE_CHANGE_CASES],
)
def test_partial_table_change_fixtures_are_reported_as_format_changed(case):
    processor = FixtureTextProcessor(_read_fixture(case))

    result = processor.process_pdf("fixture.pdf", f"{case['id']}.pdf")

    assert result["success"] is False
    assert result["parse_status"] == "format_changed"
    assert result["bank_detected"] == case["bank_id"]
    assert result["format_id"] == case["format_id"]
    assert result["diagnostics"]["transactions_found"] == 0


def test_guard_rejected_row_fails_change_detection_even_with_valid_transaction():
    text = "\n".join(
        [
            "Resumen de Caja de Ahorro en Pesos",
            "Datos de la cuenta",
            "Número de cuenta",
            "N 4046017-6 335-0",
            "Movimientos",
            "Fecha Descripción Origen Crédito Débito Saldo",
            "25/08/23 TRANSFERENCIA VALIDA 100,00 100,00",
            "26/08/23 TRANSFERENCIA DESPLAZADA 10,00 0,00 110,00",
            "Banco de Galicia y Buenos Aires S.A.U.",
        ]
    )
    spec = _load_spec(Path("parser_specs/galicia_ar/default/spec.toml"))

    spec_result = spec.parse_transactions(text)
    process_result = FixtureTextProcessor(text).process_pdf("fixture.pdf", "galicia_mixed_partial_change.pdf")

    assert spec_result.diagnostics["transactions_found"] == 1
    assert spec_result.diagnostics["rejected_matches"] == 1
    assert spec_result.passes_change_detection is False
    assert process_result["success"] is False
    assert process_result["parse_status"] == "format_changed"
    assert process_result["diagnostics"]["rejected_matches"] == 1


def test_guard_rejected_row_checks_base_description_before_multiline_continuation():
    text = "\n".join(
        [
            "Resumen de Caja de Ahorro en Pesos",
            "Datos de la cuenta",
            "Número de cuenta",
            "N 4046017-6 335-0",
            "Movimientos",
            "Fecha Descripción Origen Crédito Débito Saldo",
            "26/08/23 TRANSFERENCIA DESPLAZADA 10,00 0,00 110,00",
            "DETALLE ADICIONAL",
            "Banco de Galicia y Buenos Aires S.A.U.",
        ]
    )
    spec = _load_spec(Path("parser_specs/galicia_ar/default/spec.toml"))

    spec_result = spec.parse_transactions(text)
    process_result = FixtureTextProcessor(text).process_pdf("fixture.pdf", "galicia_multiline_partial_change.pdf")

    assert spec_result.diagnostics["transactions_found"] == 0
    assert spec_result.diagnostics["rejected_matches"] == 1
    assert spec_result.passes_change_detection is False
    assert process_result["success"] is False
    assert process_result["parse_status"] == "format_changed"
    assert process_result["diagnostics"]["rejected_matches"] == 1


def test_guard_rejects_ungrouped_four_digit_amount_tail():
    changed_rows = [
        "02/05 Payment Alpha $1900.00 $1.00",
        "02/06 Payment Beta $2300.00 $1.00",
        "02/07 Payment Gamma $4500.00 $1.00",
        "02/08 Payment Delta $1200.00 $1.00",
        "02/09 Payment Epsilon $1000.00 $1.00",
    ]
    text = "\n".join(
        [
            "JPMorgan Chase Bank, N.A.",
            "000000771927196",
            "Statement through February 29, 2024",
            "DEPOSITS AND ADDITIONS",
            *changed_rows,
            "Total Deposits and Additions $5.00",
            "ELECTRONIC WITHDRAWALS",
            "Total Electronic Withdrawals $0.00",
        ]
    )
    spec = _load_spec(Path("parser_specs/chase/default/spec.toml"))

    spec_result = spec.parse_transactions(text)
    process_result = FixtureTextProcessor(text).process_pdf("fixture.pdf", "chase_ungrouped_partial_change.pdf")

    assert spec_result.diagnostics["transactions_found"] == 0
    assert spec_result.diagnostics["rejected_matches"] == len(changed_rows)
    assert spec_result.passes_change_detection is False
    assert process_result["success"] is False
    assert process_result["parse_status"] == "format_changed"
    assert process_result["diagnostics"]["rejected_matches"] == len(changed_rows)
