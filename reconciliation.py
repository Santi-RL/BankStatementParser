from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import re

from utils import clean_text, parse_amount


INDIVIDUAL_RECONCILIATION_STATUSES = {"passed", "failed", "not_available"}


def compile_reconciliation_config(data: Dict[str, Any]) -> Dict[str, Any]:
    def compile_pattern(pattern: str) -> Optional[re.Pattern[str]]:
        return re.compile(pattern, re.IGNORECASE) if pattern else None

    sections = []
    for section in data.get("sections", []):
        sections.append(
            {
                "name": section.get("name", "reconciliation"),
                "scope_id": section.get("scope_id", ""),
                "currency": section.get("currency", ""),
                "opening_pattern": compile_pattern(section.get("opening_pattern", "")),
                "credits_pattern": compile_pattern(section.get("credits_pattern", "")),
                "debits_pattern": compile_pattern(section.get("debits_pattern", "")),
                "closing_pattern": compile_pattern(section.get("closing_pattern", "")),
            }
        )

    period_pattern = data.get("period_pattern", "")
    return {
        "supported": bool(sections),
        "tolerance": Decimal(str(data.get("tolerance", "0.01"))),
        "precision": Decimal(str(data.get("precision", "0.01"))),
        "period_pattern": (
            re.compile(period_pattern, re.IGNORECASE | re.MULTILINE)
            if period_pattern
            else None
        ),
        "period_date_formats": [
            value for value in data.get("period_date_formats", []) if value
        ],
        "sections": sections,
    }


def _decimal_from_match(
    match: Optional[re.Match[str]],
    group_name: str,
) -> Optional[Decimal]:
    if match is None:
        return None
    value = match.groupdict().get(group_name)
    if not value:
        return None
    return Decimal(str(parse_amount(value)))


def _find_match(
    pattern: Optional[re.Pattern[str]],
    lines: List[str],
) -> Optional[re.Match[str]]:
    if pattern is None:
        return None
    for line in lines:
        match = pattern.search(line)
        if match:
            return match
    return None


def _normalize_period_date(value: str, formats: List[str]) -> str:
    month_aliases = {
        "ene": "Jan",
        "feb": "Feb",
        "mar": "Mar",
        "abr": "Apr",
        "may": "May",
        "jun": "Jun",
        "jul": "Jul",
        "ago": "Aug",
        "sep": "Sep",
        "oct": "Oct",
        "nov": "Nov",
        "dic": "Dec",
    }
    normalized = clean_text(value)
    for source, target in month_aliases.items():
        normalized = re.sub(source, target, normalized, flags=re.IGNORECASE)
    for date_format in formats:
        try:
            return datetime.strptime(normalized, date_format).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return clean_text(value)


def _extract_period(text: str, config: Dict[str, Any]) -> tuple[str, str]:
    pattern = config.get("period_pattern")
    if pattern is None:
        return "", ""
    match = pattern.search(text)
    if match is None:
        return "", ""
    groups = match.groupdict()
    formats = config.get("period_date_formats", [])
    return (
        _normalize_period_date(groups.get("period_start", ""), formats),
        _normalize_period_date(groups.get("period_end", ""), formats),
    )


def _scope_metadata(
    scope_id: str,
    scopes_by_id: Dict[str, Dict[str, Any]],
    *,
    currency: str = "",
) -> Dict[str, Any]:
    scope = scopes_by_id.get(scope_id, {})
    return {
        "scope_id": scope_id,
        "scope_label": scope.get("label", ""),
        "product_type": scope.get("product_type", ""),
        "account": scope.get("account", ""),
        "currency": scope.get("currency") or currency,
    }


def build_reconciliations(
    config: Dict[str, Any],
    text: str,
    transactions: List[Dict[str, Any]],
    available_scopes: List[Dict[str, Any]],
    selected_scope_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if not config.get("supported"):
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    scopes_by_id = {scope.get("id", ""): scope for scope in available_scopes}
    selected = set(selected_scope_ids or [])
    period_start, period_end = _extract_period(text, config)
    opening_patterns = [
        section["opening_pattern"]
        for section in config["sections"]
        if section.get("opening_pattern") is not None
    ]
    reconciliations: List[Dict[str, Any]] = []

    for section in config["sections"]:
        opening_pattern = section.get("opening_pattern")
        if opening_pattern is None:
            continue
        scope_id = section.get("scope_id", "")
        if selected and scope_id not in selected:
            continue

        opening_index = None
        opening_match = None
        for index, line in enumerate(lines):
            candidate = opening_pattern.search(line)
            if candidate:
                opening_index = index
                opening_match = candidate
                break
        if opening_index is None or opening_match is None:
            continue

        end_index = len(lines)
        for index in range(opening_index + 1, len(lines)):
            if any(pattern.search(lines[index]) for pattern in opening_patterns):
                end_index = index
                break
        block_lines = lines[opening_index:end_index]

        opening_balance = _decimal_from_match(opening_match, "opening_balance")
        credits = _decimal_from_match(
            _find_match(section.get("credits_pattern"), block_lines),
            "credits",
        )
        debits = _decimal_from_match(
            _find_match(section.get("debits_pattern"), block_lines),
            "debits",
        )
        closing_balance = _decimal_from_match(
            _find_match(section.get("closing_pattern"), block_lines),
            "closing_balance",
        )

        net_movements = sum(
            (
                Decimal(str(transaction.get("amount", 0)))
                for transaction in transactions
                if transaction.get("scope_id", "") == scope_id
            ),
            Decimal("0"),
        )
        precision = config["precision"]
        net_movements = net_movements.quantize(precision)
        calculated_closing: Optional[Decimal] = None
        difference: Optional[Decimal] = None
        if opening_balance is not None and closing_balance is not None:
            calculated_closing = (opening_balance + net_movements).quantize(precision)
            difference = (closing_balance - calculated_closing).quantize(precision)
            status = (
                "passed"
                if abs(difference) <= config["tolerance"]
                else "failed"
            )
            reason = "balanced" if status == "passed" else "difference"
        else:
            status = "not_available"
            reason = "missing_summary_values"

        reconciliation = {
            **_scope_metadata(
                scope_id,
                scopes_by_id,
                currency=section.get("currency", ""),
            ),
            "period_start": period_start,
            "period_end": period_end,
            "opening_balance": (
                float(opening_balance) if opening_balance is not None else ""
            ),
            "credits": float(credits) if credits is not None else "",
            "debits": float(debits) if debits is not None else "",
            "net_movements": float(net_movements),
            "calculated_closing_balance": (
                float(calculated_closing)
                if calculated_closing is not None
                else ""
            ),
            "closing_balance": (
                float(closing_balance) if closing_balance is not None else ""
            ),
            "difference": float(difference) if difference is not None else "",
            "status": status,
            "reason": reason,
        }
        reconciliations.append(reconciliation)

    return reconciliations


def prepare_reconciliation_output(
    reconciliations: List[Dict[str, Any]],
    *,
    supports_reconciliation: bool,
    available_scopes: List[Dict[str, Any]],
    transactions: List[Dict[str, Any]],
    selected_scope_ids: Optional[List[str]],
    source_file: str,
    bank_name: str,
    format_id: str,
) -> List[Dict[str, Any]]:
    records = [dict(record) for record in reconciliations]
    selected = set(selected_scope_ids or [])
    scopes = [
        scope
        for scope in available_scopes
        if not selected or scope.get("id", "") in selected
    ]
    if not scopes and transactions:
        first = transactions[0]
        scopes = [
            {
                "id": first.get("scope_id", ""),
                "label": first.get("scope_label") or first.get("account", ""),
                "product_type": first.get("product_type", ""),
                "account": first.get("account", ""),
                "currency": first.get("currency", ""),
            }
        ]
    if not scopes and not records:
        scopes = [{}]

    present_scope_ids = {record.get("scope_id", "") for record in records}
    reason = "summary_not_found" if supports_reconciliation else "not_supported"
    for scope in scopes:
        scope_id = scope.get("id", "")
        if scope_id in present_scope_ids:
            continue
        records.append(
            {
                **_scope_metadata(scope_id, {scope_id: scope}),
                "period_start": "",
                "period_end": "",
                "opening_balance": "",
                "credits": "",
                "debits": "",
                "net_movements": "",
                "calculated_closing_balance": "",
                "closing_balance": "",
                "difference": "",
                "status": "not_available",
                "reason": reason,
            }
        )

    for record in records:
        status = record.get("status", "not_available")
        if status not in INDIVIDUAL_RECONCILIATION_STATUSES:
            record["status"] = "not_available"
            record["reason"] = "invalid_status"
        record["source_file"] = source_file
        record["bank"] = bank_name
        record["format_id"] = format_id
    return records


def aggregate_reconciliation_status(records: List[Dict[str, Any]]) -> str:
    statuses = {record.get("status", "not_available") for record in records}
    if "failed" in statuses:
        return "failed"
    if statuses == {"passed"}:
        return "passed"
    if "passed" in statuses:
        return "partial"
    return "not_available"
