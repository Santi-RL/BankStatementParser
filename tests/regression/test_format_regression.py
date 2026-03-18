from pathlib import Path

from format_training import regress_published_specs


def test_published_spec_regression_suite_is_green():
    result = regress_published_specs()

    assert result["success"] is True
    assert result["processed"] >= 4


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
