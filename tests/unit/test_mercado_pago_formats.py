from pathlib import Path
import tomllib

from format_engine import FormatRegistry, FormatSpec


FIXTURE_PATH = Path("parser_specs/mercado_pago/account_summary_pesos/fixtures/sample_text.txt")
SPEC_PATH = Path("parser_specs/mercado_pago/account_summary_pesos/spec.toml")


def test_registry_routes_mp_pesos():
    text = FIXTURE_PATH.read_text(encoding="utf-8")

    match = FormatRegistry().match_published(text, "mercado_pago")

    assert match is not None
    assert match.spec.bank_id == "mercado_pago"
    assert match.spec.format_id == "account_summary_pesos"


def test_mp_pesos_fixture_parses():
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    with SPEC_PATH.open("rb") as handle:
        spec = FormatSpec(SPEC_PATH, tomllib.load(handle))

    result = spec.parse_transactions(text)

    assert result.passes_change_detection is True
    assert result.diagnostics["coverage"] == 1.0
    assert len(result.available_scopes) == 1
    assert result.available_scopes[0]["label"] == "CVU 0000003100000000000002"
    assert len(result.transactions) == 11
    assert result.transactions[0]["amount"] == 100.0
    assert result.transactions[-1]["description"] == "Transferencia enviada PERSONA NUEVE"
