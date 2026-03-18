from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple
import json
import re

import toml

from format_engine import FormatRegistry, FormatSpec, SPEC_ROOT, load_expected_transactions
from pdf_processor import PDFProcessor


def _mask_sensitive_chunk(chunk: str) -> str:
    protected: Dict[str, str] = {}
    structural_keywords = {
        "account",
        "additions",
        "balance",
        "bank",
        "beginning",
        "business",
        "center",
        "chase",
        "checking",
        "customer",
        "deposits",
        "electronic",
        "ending",
        "fees",
        "information",
        "jpmorgan",
        "monthly",
        "online",
        "payment",
        "service",
        "summary",
        "total",
        "transfer",
        "withdrawals",
        "zelle",
    }

    def protect(match: re.Match[str]) -> str:
        key = f"__P{len(protected)}__"
        protected[key] = match.group(0)
        return key

    def replace_proper_name(match: re.Match[str]) -> str:
        value = match.group(0)
        lowered = value.lower()
        if any(keyword in lowered for keyword in structural_keywords):
            return value
        return "PERSONA"

    text = re.sub(r"\b\d{2}/\d{2}/\d{2,4}\b", protect, chunk)
    text = re.sub(r"[-+]?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}", protect, text)
    text = re.sub(r"\b(?=[A-Z0-9]{5,}\b)(?=[A-Z0-9]*\d)[A-Z0-9]+\b", lambda match: "X" * len(match.group(0)), text)
    text = re.sub(
        r"\b([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)+)\b",
        replace_proper_name,
        text,
    )

    for key, value in protected.items():
        text = text.replace(key, value)

    return text


def sanitize_fixture_text(text: str) -> str:
    return "\n".join(_mask_sensitive_chunk(line) for line in text.splitlines())


def sanitize_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for transaction in transactions:
        entry = deepcopy(transaction)
        if entry.get("description"):
            entry["description"] = _mask_sensitive_chunk(str(entry["description"]))
        if entry.get("account"):
            entry["account"] = _mask_sensitive_chunk(str(entry["account"]))
        sanitized.append(entry)
    return sanitized


def build_initial_spec(
    bank_id: str,
    format_id: str,
    display_name: str,
    country: str = "AR",
    currency_default: str = "ARS",
    extracted_text: str = "",
) -> Dict[str, Any]:
    text_lower = extracted_text.lower()

    if bank_id == "galicia_ar" or "resumen de caja de ahorro en pesos" in text_lower:
        return {
            "meta": {
                "bank_id": bank_id,
                "format_id": format_id,
                "version": 1,
                "status": "draft",
                "country": country,
                "currency_default": currency_default,
                "display_name": display_name,
            },
            "detect": {
                "required_keywords": [
                    "Resumen de Caja de Ahorro en Pesos",
                    "Movimientos",
                    "Fecha Descripción",
                ],
                "excluded_keywords": [],
                "min_score": 0.66,
            },
            "extract": {
                "strategy": "line_regex",
                "line_pattern": r"^(?P<date>\d{2}/\d{2}/\d{2})\s+(?P<description>.+?)\s+(?P<amount>[+-]?\d{1,3}(?:\.\d{3})*,\d{2})\s+(?P<balance>[+-]?\d{1,3}(?:\.\d{3})*,\d{2})$",
                "candidate_pattern": r"^\d{2}/\d{2}/\d{2}",
                "section_start_patterns": [r"^Movimientos$", r"^Fecha\s+Descripción"],
                "ignore_patterns": [
                    r"^Resumen de Caja",
                    r"^Datos de la cuenta",
                    r"^Tipo de cuenta",
                    r"^Caja de Ahorro en Pesos$",
                    r"^Número de cuenta$",
                    r"^CBU ",
                    r"^Disponés de",
                ],
                "stop_patterns": [
                    r"^Consolidado de retención",
                    r"^Los depósitos en pesos",
                    r"^Canales de atención",
                    r"^Usted puede consultar",
                    r"^Josefina M\. Quevedo",
                    r"^Banco de Galicia y Buenos Aires",
                ],
                "multiline": True,
            },
            "fields": {
                "date": "date",
                "description": "description",
                "amount": "amount",
                "balance": "balance",
                "account_pattern": r"Número de cuenta\s*\n([A-Z0-9\-\s]+)",
            },
            "normalize": {
                "date_formats": ["%d/%m/%y"],
            },
            "change_detection": {
                "min_transactions": 3,
                "min_match_ratio": 0.7,
            },
        }

    if bank_id == "chase" or ("jpmorgan chase bank" in text_lower and "deposits and additions" in text_lower):
        return {
            "meta": {
                "bank_id": bank_id,
                "format_id": format_id,
                "version": 1,
                "status": "draft",
                "country": "US",
                "currency_default": "USD",
                "display_name": display_name,
            },
            "detect": {
                "required_keywords": [
                    "JPMorgan Chase Bank, N.A.",
                    "DEPOSITS AND ADDITIONS",
                    "ELECTRONIC WITHDRAWALS",
                ],
                "excluded_keywords": [],
                "min_score": 0.66,
            },
            "extract": {
                "strategy": "line_regex",
                "sections": [
                    {
                        "name": "deposits",
                        "start_patterns": [r"^DEPOSITS AND ADDITIONS$"],
                        "stop_patterns": [r"^Total Deposits and Additions"],
                        "line_pattern": r"^(?P<date>\d{2}/\d{2})\s+(?P<description>.+?)\s+(?P<amount>\$?[\d,]+\.\d{2})$",
                        "candidate_pattern": r"^\d{2}/\d{2}\s+",
                        "multiline": False,
                        "amount_sign": "positive",
                    },
                    {
                        "name": "withdrawals",
                        "start_patterns": [r"^ELECTRONIC WITHDRAWALS$"],
                        "stop_patterns": [r"^Total Electronic Withdrawals"],
                        "line_pattern": r"^(?P<date>\d{2}/\d{2})\s+(?P<description>.+?)\s+(?P<amount>\$?[\d,]+\.\d{2})$",
                        "candidate_pattern": r"^\d{2}/\d{2}\s+",
                        "multiline": False,
                        "amount_sign": "negative",
                    },
                    {
                        "name": "fees",
                        "start_patterns": [r"^FEES$"],
                        "stop_patterns": [r"^Total Fees"],
                        "line_pattern": r"^(?P<date>\d{2}/\d{2})\s+(?P<description>.+?)\s+(?P<amount>\$?[\d,]+\.\d{2})$",
                        "candidate_pattern": r"^\d{2}/\d{2}\s+",
                        "multiline": False,
                        "amount_sign": "negative",
                    },
                ],
            },
            "fields": {
                "date": "date",
                "description": "description",
                "amount": "amount",
                "balance": "",
                "account_pattern": r"(?m)^(\d{15})$",
            },
            "normalize": {
                "date_formats": ["%m/%d"],
                "statement_year_pattern": r"through.*?(?P<year>20\d{2})",
            },
            "change_detection": {
                "min_transactions": 5,
                "min_match_ratio": 0.9,
            },
        }

    if bank_id == "roela_ar" or "resumen de cuenta corriente" in text_lower:
        return {
            "meta": {
                "bank_id": bank_id,
                "format_id": format_id,
                "version": 1,
                "status": "draft",
                "country": country,
                "currency_default": currency_default,
                "display_name": display_name,
            },
            "detect": {
                "required_keywords": [
                    "RESUMEN DE CUENTA CORRIENTE",
                    "CODIGO COMPROBANTE CONCEPTO DEBITOS CREDITOS",
                    "C.B.U.",
                ],
                "excluded_keywords": [],
                "min_score": 0.66,
            },
            "extract": {
                "strategy": "line_regex",
                "pdf_text_strategy": "roela_columns",
                "pdf_text_options": {
                    "header_cut": 260.0,
                    "footer_cut": 30.0,
                    "split_ratio": 0.515,
                    "margin_pt": 0.0,
                    "stop_keyword": "DE INTERES PARA USTED",
                },
                "line_pattern": r"^(?P<code>[A-Za-z]?\d+)\s+(?P<reference>\S+)\s+(?P<description>.+?)\s+(?P<amount>\d{1,3}(?:,\d{3})*\.\d{2})$",
                "candidate_pattern": r"^(?:\d{2}/\d{2}/\d{4}\s+)?[A-Za-z]?\d+\s+\S+\s+.+\d{1,3}(?:,\d{3})*\.\d{2}$",
                "current_date_pattern": r"^(?P<date>\d{2}/\d{2}/\d{4})\s*",
                "strip_current_date": True,
                "section_start_patterns": [],
                "ignore_patterns": [
                    r"^IMPORTANTE",
                    r"^Titular/",
                    r"^Situación IVA",
                    r"^C\.B\.U\.",
                    r"^Domicilio",
                    r"^Período ",
                    r"^Fecha de Impresión",
                    r"^Hora de Impresión",
                    r"^SALDO AL ",
                ],
                "stop_patterns": [r"^DE INTERES PARA USTED"],
                "multiline": True,
                "amount_sign": "rule_based",
                "sign_rules": {
                    "field": "code",
                    "default": "debit",
                    "debit_codes": [
                        "309", "313", "314", "317", "318", "319", "320", "321", "322", "323",
                        "386", "396", "300100", "700100", "710100", "750100", "760100", "810100",
                        "860100", "880100", "F30100",
                    ],
                    "credit_codes": [
                        "305", "310", "324", "325", "332", "333", "334", "335",
                        "720100", "740100", "770100", "F40001",
                    ],
                    "prefix_defaults": {
                        "1": "debit",
                        "2": "debit",
                        "4": "credit",
                        "5": "credit",
                    },
                    "prefix_credit_overrides": {
                        "2": ["290", "291", "296", "200001", "240001", "290001"],
                    },
                    "prefix_debit_overrides": {
                        "4": ["400101", "400111"],
                        "5": ["557", "583", "585", "586", "593", "594", "500131"],
                    },
                },
            },
            "fields": {
                "date": "date",
                "description": "description",
                "description_template": "{code} {reference} {description}",
                "amount": "amount",
                "balance": "",
                "account_pattern": r"Cuenta\s*:?\s*(\d+/\d+)",
            },
            "normalize": {
                "date_formats": ["%d/%m/%Y"],
            },
            "change_detection": {
                "min_transactions": 10,
                "min_match_ratio": 0.5,
            },
        }

    return {
        "meta": {
            "bank_id": bank_id,
            "format_id": format_id,
            "version": 1,
            "status": "draft",
            "country": country,
            "currency_default": currency_default,
            "display_name": display_name,
        },
        "detect": {
            "required_keywords": [line for line in extracted_text.splitlines()[:3] if line.strip()],
            "excluded_keywords": [],
            "min_score": 0.5,
        },
        "extract": {
            "strategy": "line_regex",
            "line_pattern": r"^(?P<date>\d{2}/\d{2}/\d{2,4})\s+(?P<description>.+?)\s+(?P<amount>[+-]?\d{1,3}(?:[.,]\d{3})*[.,]\d{2})(?:\s+(?P<balance>[+-]?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}))?$",
            "candidate_pattern": r"^\d{2}/\d{2}/\d{2,4}",
            "section_start_patterns": [],
            "ignore_patterns": [],
            "stop_patterns": [],
            "multiline": True,
        },
        "fields": {
            "date": "date",
            "description": "description",
            "amount": "amount",
            "balance": "balance",
            "account_pattern": "",
        },
        "normalize": {
            "date_formats": ["%d/%m/%y", "%d/%m/%Y"],
        },
        "change_detection": {
            "min_transactions": 1,
            "min_match_ratio": 0.4,
        },
    }


def spec_directory(bank_id: str, format_id: str, root: Path | None = None) -> Path:
    base_root = root or SPEC_ROOT
    return base_root / bank_id / format_id


def save_draft(
    spec_data: Dict[str, Any],
    extracted_text: str,
    expected_transactions: List[Dict[str, Any]],
    root: Path | None = None,
) -> Path:
    bank_id = spec_data["meta"]["bank_id"]
    format_id = spec_data["meta"]["format_id"]
    spec_dir = spec_directory(bank_id, format_id, root=root)
    fixture_dir = spec_dir / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)

    spec_path = spec_dir / "spec.toml"
    spec_path.write_text(toml.dumps(spec_data), encoding="utf-8")
    sanitized_text = sanitize_fixture_text(extracted_text)
    (fixture_dir / "sample_text.txt").write_text(sanitized_text, encoding="utf-8")

    expected_payload = sanitize_transactions(expected_transactions)
    parsed_from_sanitized = FormatSpec(spec_path, spec_data).parse_transactions(sanitized_text).transactions
    if parsed_from_sanitized:
        expected_payload = sanitize_transactions(parsed_from_sanitized)
    (fixture_dir / "expected_transactions.json").write_text(
        json.dumps(expected_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return spec_path


def publish_spec(spec_path: Path) -> Path:
    spec_data = toml.loads(spec_path.read_text(encoding="utf-8"))
    spec_data.setdefault("meta", {})
    spec_data["meta"]["status"] = "published"
    spec_data["meta"]["version"] = int(spec_data["meta"].get("version", 1))
    spec_path.write_text(toml.dumps(spec_data), encoding="utf-8")
    return spec_path


def validate_spec(spec_path: Path, text: str, pdf_path: str | None = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
    spec_data = toml.loads(spec_path.read_text(encoding="utf-8"))
    spec = FormatSpec(spec_path, spec_data)
    prepared_text = spec.prepare_text(text, pdf_path)
    result = spec.parse_transactions(prepared_text)
    return result.transactions, result.diagnostics, result.passes_change_detection


def regress_published_specs(root: Path | None = None) -> Dict[str, Any]:
    registry = FormatRegistry(root)
    failures: List[Dict[str, Any]] = []
    processed = 0
    for spec in registry.specs_by_status("published"):
        processed += 1
        text_path = spec.fixture_dir / "sample_text.txt"
        expected_path = spec.fixture_dir / "expected_transactions.json"
        if not text_path.exists() or not expected_path.exists():
            failures.append(
                {
                    "spec": f"{spec.bank_id}/{spec.format_id}",
                    "reason": "missing_fixture",
                }
            )
            continue

        text = text_path.read_text(encoding="utf-8")
        expected = load_expected_transactions(expected_path)
        parsed = spec.parse_transactions(text)
        actual = sanitize_transactions(parsed.transactions)
        if not parsed.passes_change_detection or actual != expected:
            failures.append(
                {
                    "spec": f"{spec.bank_id}/{spec.format_id}",
                    "reason": "regression",
                    "diagnostics": parsed.diagnostics,
                    "expected_count": len(expected),
                    "actual_count": len(actual),
                }
            )

    return {
        "processed": processed,
        "failures": failures,
        "success": not failures,
    }


def extract_text_from_pdf(pdf_path: str) -> str:
    processor = PDFProcessor()
    return processor._extract_text_from_pdf(pdf_path)
