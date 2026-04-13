from pathlib import Path
import tomllib

from format_engine import FormatRegistry, FormatSpec
from format_training import (
    build_initial_spec,
    publish_spec,
    regress_published_specs,
    save_draft,
    validate_spec,
)


def test_registry_matches_published_galicia_spec():
    registry = FormatRegistry()
    fixture_path = Path("parser_specs/galicia_ar/default/fixtures/sample_text.txt")
    text = fixture_path.read_text(encoding="utf-8")

    match = registry.match_published(text, "galicia_ar")

    assert match is not None
    assert match.spec.bank_id == "galicia_ar"
    assert match.spec.format_id == "default"


def test_registry_matches_published_chase_spec():
    registry = FormatRegistry()
    fixture_path = Path("parser_specs/chase/default/fixtures/sample_text.txt")
    text = fixture_path.read_text(encoding="utf-8")

    match = registry.match_published(text, "chase")

    assert match is not None
    assert match.spec.bank_id == "chase"
    assert match.spec.format_id == "default"


def test_registry_matches_published_roela_spec():
    registry = FormatRegistry()
    fixture_path = Path("parser_specs/roela_ar/default/fixtures/sample_text.txt")
    text = fixture_path.read_text(encoding="utf-8")

    match = registry.match_published(text, "roela_ar")

    assert match is not None
    assert match.spec.bank_id == "roela_ar"
    assert match.spec.format_id == "default"


def test_registry_matches_published_bbva_account_summary_spec():
    registry = FormatRegistry()
    fixture_path = Path("parser_specs/bbva/account_summary/fixtures/sample_text.txt")
    text = fixture_path.read_text(encoding="utf-8")

    match = registry.match_published(text, "bbva")

    assert match is not None
    assert match.spec.bank_id == "bbva"
    assert match.spec.format_id == "account_summary"


def test_registry_matches_published_mercado_pago_spec():
    registry = FormatRegistry()
    fixture_path = Path("parser_specs/mercado_pago/default/fixtures/sample_text.txt")
    text = fixture_path.read_text(encoding="utf-8")

    match = registry.match_published(text, "mercado_pago")

    assert match is not None
    assert match.spec.bank_id == "mercado_pago"
    assert match.spec.format_id == "default"


def test_registry_matches_published_brubank_spec():
    registry = FormatRegistry()
    fixture_path = Path("parser_specs/brubank/default/fixtures/sample_text.txt")
    text = fixture_path.read_text(encoding="utf-8")

    match = registry.match_published(text, "brubank")

    assert match is not None
    assert match.spec.bank_id == "brubank"
    assert match.spec.format_id == "default"


def test_save_draft_and_publish(tmp_path):
    spec = build_initial_spec(
        bank_id="demo_bank",
        format_id="draft_alpha",
        display_name="Demo Bank",
        extracted_text="01/01/25 TEST 10,00 10,00",
    )
    spec_path = save_draft(
        spec,
        extracted_text="01/01/25 TEST 10,00 10,00",
        expected_transactions=[],
        root=tmp_path,
    )

    assert spec_path.exists()

    publish_spec(spec_path)
    registry = FormatRegistry(tmp_path)
    registry.refresh()
    loaded = registry.get_spec("demo_bank", "draft_alpha")

    assert loaded is not None
    assert loaded.status == "published"


def test_validate_spec_and_regressions():
    fixture_path = Path("parser_specs/galicia_ar/default/fixtures/sample_text.txt")
    spec_path = Path("parser_specs/galicia_ar/default/spec.toml")
    text = fixture_path.read_text(encoding="utf-8")

    transactions, diagnostics, ok = validate_spec(spec_path, text)
    regression = regress_published_specs()

    assert ok is True
    assert len(transactions) == 3
    assert diagnostics["coverage"] >= 1.0
    assert regression["success"] is True


def test_chase_spec_infers_statement_year_and_section_signs():
    fixture_path = Path("parser_specs/chase/default/fixtures/sample_text.txt")
    spec_path = Path("parser_specs/chase/default/spec.toml")
    text = fixture_path.read_text(encoding="utf-8")

    transactions, diagnostics, ok = validate_spec(spec_path, text)

    assert ok is True
    assert diagnostics["statement_year"] == 2024
    assert len(transactions) == 12
    assert transactions[0]["date"] == "2024-01-02"
    assert transactions[4]["amount"] < 0


def test_roela_spec_handles_rule_based_signs():
    fixture_path = Path("parser_specs/roela_ar/default/fixtures/sample_text.txt")
    spec_path = Path("parser_specs/roela_ar/default/spec.toml")
    text = fixture_path.read_text(encoding="utf-8")

    transactions, diagnostics, ok = validate_spec(spec_path, text)

    assert ok is True
    assert diagnostics["transactions_found"] >= 50
    assert any(transaction["amount"] > 0 for transaction in transactions)
    assert any(transaction["amount"] < 0 for transaction in transactions)


def test_bbva_spec_discovers_scopes_and_filters_selected_entities():
    fixture_path = Path("parser_specs/bbva/default/fixtures/sample_text.txt")
    spec_path = Path("parser_specs/bbva/default/spec.toml")
    text = fixture_path.read_text(encoding="utf-8")

    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    full_result = spec.parse_transactions(text)
    account_scope_ids = [
        scope["id"]
        for scope in full_result.available_scopes
        if scope["product_type"] == "bank_account"
    ]
    account_result = spec.parse_transactions(text, selected_scope_ids=account_scope_ids)

    assert len(full_result.available_scopes) == 5
    assert any(scope["product_type"] == "credit_card" for scope in full_result.available_scopes)
    assert all(transaction["product_type"] == "bank_account" for transaction in account_result.transactions)
    assert {transaction["scope_label"] for transaction in account_result.transactions} == {
        "CA $ 354-428727/2",
        "CC $ 354-560404/1",
    }


def test_bbva_account_summary_spec_parses_single_scope_account_statement():
    fixture_path = Path("parser_specs/bbva/account_summary/fixtures/sample_text.txt")
    spec_path = Path("parser_specs/bbva/account_summary/spec.toml")
    text = fixture_path.read_text(encoding="utf-8")

    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    result = spec.parse_transactions(text)

    assert result.passes_change_detection is True
    assert result.diagnostics["statement_year"] == 2023
    assert len(result.available_scopes) == 1
    assert result.available_scopes[0]["label"] == "CA $ 354-428727/2"
    assert len(result.transactions) == 12
    assert result.transactions[0]["date"] == "2023-08-22"
    assert result.transactions[-1]["amount"] == -2572.98


def test_mercado_pago_spec_parses_wallet_fixture():
    fixture_path = Path("parser_specs/mercado_pago/default/fixtures/sample_text.txt")
    spec_path = Path("parser_specs/mercado_pago/default/spec.toml")
    text = fixture_path.read_text(encoding="utf-8")

    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    result = spec.parse_transactions(text)

    assert result.passes_change_detection is True
    assert len(result.available_scopes) == 1
    assert result.available_scopes[0]["label"] == "CVU 0000003100000000000001"
    assert len(result.transactions) == 11
    assert result.transactions[0]["amount"] == -15950.0
    assert result.transactions[-1]["description"] == "Transferencia recibida PERSONA DIEZ"


def test_brubank_spec_parses_debit_and_credit_columns_fixture():
    fixture_path = Path("parser_specs/brubank/default/fixtures/sample_text.txt")
    spec_path = Path("parser_specs/brubank/default/spec.toml")
    text = fixture_path.read_text(encoding="utf-8")

    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    result = spec.parse_transactions(text)

    assert result.passes_change_detection is True
    assert len(result.transactions) == 34
    assert result.transactions[0]["amount"] == -47000.0
    assert result.transactions[6]["amount"] == 712500.0
    assert result.transactions[-1]["amount"] == 24955.31
