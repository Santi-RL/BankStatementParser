from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import logging
import re
import string
import tomllib

try:
    import pdfplumber
except Exception:  # pragma: no cover - optional dependency
    pdfplumber = None

from utils import clean_text, parse_amount, parse_date


SPEC_ROOT = Path("parser_specs")


def _load_toml(path: Path) -> Dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


@dataclass
class SpecMatch:
    spec: "FormatSpec"
    score: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    excluded_hits: List[str]


@dataclass
class SpecParseResult:
    transactions: List[Dict[str, Any]]
    diagnostics: Dict[str, Any]
    passes_change_detection: bool
    available_scopes: List[Dict[str, Any]]


class _DefaultTemplateDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


class FormatSpec:
    def __init__(self, source_path: Path, data: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.source_path = source_path
        self.data = data
        self.meta = data.get("meta", {})
        self.detect = data.get("detect", {})
        self.extract = data.get("extract", {})
        self.fields = data.get("fields", {})
        self.normalize = data.get("normalize", {})
        self.change_detection = data.get("change_detection", {})

        self.bank_id: str = self.meta["bank_id"]
        self.format_id: str = self.meta["format_id"]
        self.version: int = int(self.meta.get("version", 1))
        self.status: str = self.meta.get("status", "draft")
        self.display_name: str = self.meta.get("display_name", self.bank_id.replace("_", " ").title())
        self.currency_default: str = self.meta.get("currency_default", "ARS")

        self.required_keywords = [keyword for keyword in self.detect.get("required_keywords", []) if keyword]
        self.excluded_keywords = [keyword for keyword in self.detect.get("excluded_keywords", []) if keyword]
        self.min_score = float(self.detect.get("min_score", 0.5))

        self.section_start_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.extract.get("section_start_patterns", [])]
        self.ignore_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.extract.get("ignore_patterns", [])]
        self.stop_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.extract.get("stop_patterns", [])]
        self.pdf_text_strategy = self.extract.get("pdf_text_strategy", "")
        self.pdf_text_options = self.extract.get("pdf_text_options", {})
        self.line_pattern = re.compile(self.extract["line_pattern"]) if self.extract.get("line_pattern") else None
        self.candidate_pattern = re.compile(
            self.extract.get("candidate_pattern", r"^\d{2}/\d{2}/\d{2}")
        ) if self.extract.get("candidate_pattern", r"^\d{2}/\d{2}/\d{2}") else None
        self.multiline = bool(self.extract.get("multiline", True))
        self.current_date_pattern = (
            re.compile(self.extract["current_date_pattern"]) if self.extract.get("current_date_pattern") else None
        )
        self.strip_current_date = bool(self.extract.get("strip_current_date", True))
        self.scope_definitions = [self._compile_scope_definition(scope) for scope in data.get("scopes", [])]
        self.section_configs = [self._compile_section(section) for section in self.extract.get("sections", [])]

        self.account_pattern = self.fields.get("account_pattern")
        self.account_regex = re.compile(self.account_pattern, re.IGNORECASE | re.MULTILINE) if self.account_pattern else None

        self.date_formats = [fmt for fmt in self.normalize.get("date_formats", []) if fmt]
        self.statement_year_pattern = self.normalize.get("statement_year_pattern", "")
        self.statement_year_regex = (
            re.compile(self.statement_year_pattern, re.IGNORECASE | re.MULTILINE)
            if self.statement_year_pattern
            else None
        )
        self.statement_month_pattern = self.normalize.get("statement_month_pattern", "")
        self.statement_month_regex = (
            re.compile(self.statement_month_pattern, re.IGNORECASE | re.MULTILINE)
            if self.statement_month_pattern
            else None
        )

        self.min_transactions = int(self.change_detection.get("min_transactions", 1))
        self.min_match_ratio = float(self.change_detection.get("min_match_ratio", 0.5))
        self.supports_explicit_scopes = bool(
            self.scope_definitions
            or any(
                section.get("default_scope_product_type")
                or section.get("default_scope_id")
                or section.get("context_rules")
                for section in self.section_configs
            )
        )

    @property
    def fixture_dir(self) -> Path:
        return self.source_path.parent / "fixtures"

    def _compile_section(self, section: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": section.get("name", "section"),
            "start_patterns": [re.compile(pattern, re.IGNORECASE) for pattern in section.get("start_patterns", [])],
            "stop_patterns": [re.compile(pattern, re.IGNORECASE) for pattern in section.get("stop_patterns", [])],
            "ignore_patterns": [re.compile(pattern, re.IGNORECASE) for pattern in section.get("ignore_patterns", [])],
            "line_pattern": re.compile(section["line_pattern"]) if section.get("line_pattern") else self.line_pattern,
            "candidate_pattern": (
                re.compile(section["candidate_pattern"], re.IGNORECASE)
                if section.get("candidate_pattern")
                else self.candidate_pattern
            ),
            "multiline": bool(section.get("multiline", self.multiline)),
            "amount_sign": section.get("amount_sign", "as_is"),
            "sign_rules": section.get("sign_rules", self.extract.get("sign_rules", {})),
            "default_scope_id": section.get("default_scope_id", ""),
            "default_scope_product_type": section.get("default_scope_product_type", ""),
            "context_rules": [self._compile_context_rule(rule) for rule in section.get("context_rules", [])],
        }

    def _compile_scope_definition(self, scope: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": scope.get("name", "scope"),
            "pattern": re.compile(scope["pattern"], re.IGNORECASE | re.MULTILINE),
            "scope_id_template": scope.get("scope_id_template", scope.get("id_template", "")),
            "label_template": scope.get("label_template", ""),
            "product_type": scope.get("product_type", ""),
            "account_template": scope.get("account_template", ""),
            "currency_template": scope.get("currency_template", ""),
            "currency_value": scope.get("currency", ""),
            "linked_account_template": scope.get("linked_account_template", ""),
            "source_sections": list(scope.get("source_sections", [])),
        }

    def _compile_context_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": rule.get("action", "activate_scope"),
            "pattern": re.compile(rule["pattern"], re.IGNORECASE),
            "scope_lookup_field": rule.get("scope_lookup_field", ""),
            "scope_lookup_template": rule.get("scope_lookup_template", ""),
            "scope_id_template": rule.get("scope_id_template", ""),
            "label_template": rule.get("label_template", ""),
            "product_type": rule.get("product_type", ""),
            "account_template": rule.get("account_template", ""),
            "currency_template": rule.get("currency_template", ""),
            "currency_value": rule.get("currency", ""),
            "linked_account_template": rule.get("linked_account_template", ""),
            "create_if_missing": bool(rule.get("create_if_missing", True)),
        }

    def _render_template(self, template: str, values: Dict[str, Any], sanitize: bool = True) -> str:
        if not template:
            return ""
        formatter = string.Formatter()
        field_names = [field_name for _, field_name, _, _ in formatter.parse(template) if field_name]
        if not field_names:
            return template
        rendered = template.format_map(_DefaultTemplateDict({key: "" if value is None else str(value) for key, value in values.items()}))
        return clean_text(rendered) if sanitize else rendered.strip()

    def _scope_values_from_templates(self, definition: Dict[str, Any], values: Dict[str, Any], default_source_section: str = "") -> Dict[str, Any]:
        source_sections = list(definition.get("source_sections", []))
        if default_source_section and default_source_section not in source_sections:
            source_sections.append(default_source_section)

        currency_map = {str(key).upper(): str(value) for key, value in self.normalize.get("currency_map", {}).items()}
        raw_currency = self._render_template(definition.get("currency_template", ""), values, sanitize=False) or definition.get("currency_value", "") or self.currency_default
        currency = currency_map.get(raw_currency.strip().upper(), raw_currency.strip())
        return {
            "id": self._render_template(definition.get("scope_id_template", ""), values, sanitize=False),
            "label": self._render_template(definition.get("label_template", ""), values),
            "product_type": definition.get("product_type", ""),
            "account": self._render_template(definition.get("account_template", ""), values),
            "currency": currency,
            "linked_account": self._render_template(definition.get("linked_account_template", ""), values),
            "source_sections": source_sections,
        }

    def _merge_scope(self, existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(existing)
        for key in ("label", "product_type", "account", "currency", "linked_account"):
            if incoming.get(key):
                merged[key] = incoming[key]
        source_sections = list(existing.get("source_sections", []))
        for section_name in incoming.get("source_sections", []):
            if section_name and section_name not in source_sections:
                source_sections.append(section_name)
        merged["source_sections"] = source_sections
        return merged

    def _ensure_scope(self, scope_registry: Dict[str, Dict[str, Any]], scope_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        scope_id = scope_data.get("id", "")
        if not scope_id:
            return None
        if scope_id in scope_registry:
            scope_registry[scope_id] = self._merge_scope(scope_registry[scope_id], scope_data)
        else:
            if not scope_data.get("label"):
                scope_data["label"] = scope_id
            scope_data.setdefault("product_type", "")
            scope_data.setdefault("account", "")
            scope_data.setdefault("currency", self.currency_default)
            scope_data.setdefault("linked_account", "")
            scope_data.setdefault("source_sections", [])
            scope_registry[scope_id] = scope_data
        return scope_registry[scope_id]

    def _scope_sort_key(self, scope: Dict[str, Any]) -> Tuple[str, str, str]:
        return (scope.get("product_type", ""), scope.get("label", ""), scope.get("id", ""))

    def discover_scopes(self, text: str) -> List[Dict[str, Any]]:
        if not self.scope_definitions:
            return []

        scope_registry: Dict[str, Dict[str, Any]] = {}
        for definition in self.scope_definitions:
            for match in definition["pattern"].finditer(text):
                groups = {key: value for key, value in match.groupdict().items() if value is not None}
                scope_data = self._scope_values_from_templates(definition, groups)
                self._ensure_scope(scope_registry, scope_data)

        return sorted(scope_registry.values(), key=self._scope_sort_key)

    def _resolve_default_scope(
        self,
        scope_registry: Dict[str, Dict[str, Any]],
        scope: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if scope.get("default_scope_id"):
            return scope_registry.get(scope["default_scope_id"])

        product_type = scope.get("default_scope_product_type", "")
        if not product_type:
            return None

        candidates = [candidate for candidate in scope_registry.values() if candidate.get("product_type") == product_type]
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _apply_context_rules(
        self,
        line: str,
        scope: Dict[str, Any],
        scope_registry: Dict[str, Dict[str, Any]],
        active_scope: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        current_scope = active_scope
        for rule in scope.get("context_rules", []):
            match = rule["pattern"].search(line)
            if not match:
                continue

            groups = {key: value for key, value in match.groupdict().items() if value is not None}
            resolved_scope: Optional[Dict[str, Any]] = None
            lookup_field = rule.get("scope_lookup_field", "")
            lookup_template = rule.get("scope_lookup_template", "")
            if lookup_field and lookup_template:
                lookup_value = self._render_template(lookup_template, groups)
                for candidate in scope_registry.values():
                    if str(candidate.get(lookup_field, "")) == lookup_value:
                        resolved_scope = candidate
                        break

            if rule["action"] == "activate_scope" and resolved_scope is None:
                scope_data = self._scope_values_from_templates(rule, groups, default_source_section=scope["name"])
                if rule.get("create_if_missing", True):
                    resolved_scope = self._ensure_scope(scope_registry, scope_data)

            if rule["action"] == "update_scope":
                target_scope = resolved_scope or current_scope
                if target_scope is None:
                    continue
                scope_data = self._scope_values_from_templates(rule, groups, default_source_section=scope["name"])
                scope_data["id"] = target_scope["id"]
                resolved_scope = self._ensure_scope(scope_registry, scope_data)

            if resolved_scope is not None:
                current_scope = resolved_scope

        return current_scope

    def prepare_text(self, text: str, file_path: Optional[str] = None) -> str:
        if self.pdf_text_strategy == "roela_columns" and file_path:
            extracted = self._extract_roela_columns_text(file_path)
            if extracted:
                return extracted
        if self.pdf_text_strategy == "x_band_table" and file_path:
            extracted = self._extract_x_band_table_text(file_path, text)
            if extracted:
                return extracted
        return text

    def evaluate(self, text: str) -> SpecMatch:
        text_lower = text.lower()
        matched_keywords = [keyword for keyword in self.required_keywords if keyword.lower() in text_lower]
        missing_keywords = [keyword for keyword in self.required_keywords if keyword.lower() not in text_lower]
        excluded_hits = [keyword for keyword in self.excluded_keywords if keyword.lower() in text_lower]

        if excluded_hits:
            return SpecMatch(self, 0.0, matched_keywords, missing_keywords, excluded_hits)

        if not self.required_keywords:
            score = 1.0
        else:
            score = len(matched_keywords) / len(self.required_keywords)

        return SpecMatch(self, score, matched_keywords, missing_keywords, excluded_hits)

    def parse_transactions(self, text: str, selected_scope_ids: Optional[List[str]] = None) -> SpecParseResult:
        account = ""
        if self.account_regex:
            match = self.account_regex.search(text)
            if match:
                account = " ".join(match.group(1).split())

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        statement_year = self._extract_statement_year(text)
        statement_month = self._extract_statement_month(text)

        transactions: List[Dict[str, Any]] = []
        candidate_lines = 0
        matched_starts = 0
        stop_reason = ""
        section_diagnostics: List[Dict[str, Any]] = []
        available_scopes = self.discover_scopes(text)
        scope_registry = {scope["id"]: dict(scope) for scope in available_scopes}

        scopes = self.section_configs or [
            {
                "name": "default",
                "start_patterns": self.section_start_patterns,
                "stop_patterns": self.stop_patterns,
                "ignore_patterns": self.ignore_patterns,
                "line_pattern": self.line_pattern,
                "candidate_pattern": self.candidate_pattern,
                "multiline": self.multiline,
                "amount_sign": self.extract.get("amount_sign", "as_is"),
                "sign_rules": self.extract.get("sign_rules", {}),
                "default_scope_id": "",
                "default_scope_product_type": "",
                "context_rules": [],
            }
        ]

        for scope in scopes:
            scope_transactions, scope_diagnostics = self._parse_scope(
                lines=lines,
                account=account,
                statement_year=statement_year,
                statement_month=statement_month,
                scope=scope,
                scope_registry=scope_registry,
                selected_scope_ids=selected_scope_ids,
            )
            transactions.extend(scope_transactions)
            candidate_lines += scope_diagnostics["candidate_lines"]
            matched_starts += scope_diagnostics["matched_starts"]
            if scope_diagnostics["stop_reason"] and not stop_reason:
                stop_reason = scope_diagnostics["stop_reason"]
            section_diagnostics.append(scope_diagnostics)

        coverage = matched_starts / candidate_lines if candidate_lines else 0.0
        passes_change_detection = len(transactions) >= self.min_transactions and coverage >= self.min_match_ratio
        diagnostics = {
            "matched_starts": matched_starts,
            "candidate_lines": candidate_lines,
            "coverage": round(coverage, 4),
            "transactions_found": len(transactions),
            "min_transactions": self.min_transactions,
            "min_match_ratio": self.min_match_ratio,
            "stop_reason": stop_reason,
            "spec_path": str(self.source_path),
            "statement_year": statement_year,
            "statement_month": statement_month,
            "sections": section_diagnostics,
            "available_scopes": sorted(scope_registry.values(), key=self._scope_sort_key),
        }
        return SpecParseResult(
            transactions=transactions,
            diagnostics=diagnostics,
            passes_change_detection=passes_change_detection,
            available_scopes=sorted(scope_registry.values(), key=self._scope_sort_key),
        )

    def _parse_scope(
        self,
        lines: List[str],
        account: str,
        statement_year: Optional[int],
        statement_month: Optional[int],
        scope: Dict[str, Any],
        scope_registry: Dict[str, Dict[str, Any]],
        selected_scope_ids: Optional[List[str]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        parsing_started = not scope["start_patterns"]
        current_match: Optional[re.Match[str]] = None
        desc_lines: List[str] = []
        current_date: Optional[str] = None
        current_scope = self._resolve_default_scope(scope_registry, scope) if self.supports_explicit_scopes else None
        current_scope_for_match: Optional[Dict[str, Any]] = current_scope
        transactions: List[Dict[str, Any]] = []
        candidate_lines = 0
        matched_starts = 0
        stop_reason = ""

        for line in lines:
            if self.supports_explicit_scopes:
                current_scope = self._apply_context_rules(line, scope, scope_registry, current_scope)

            if not parsing_started:
                if any(pattern.search(line) for pattern in scope["start_patterns"]):
                    parsing_started = True
                continue

            if any(pattern.search(line) for pattern in scope["stop_patterns"]):
                stop_reason = line
                break

            if any(pattern.search(line) for pattern in scope["ignore_patterns"]):
                continue

            working_line = line
            line_date: Optional[str] = None
            if self.current_date_pattern:
                current_date_match = self.current_date_pattern.match(working_line)
                if current_date_match:
                    line_date = self._parse_spec_date(
                        current_date_match.group("date"),
                        statement_year,
                        statement_month,
                    )
                    if self.strip_current_date:
                        working_line = working_line[current_date_match.end():].strip()
                    if not working_line:
                        if line_date:
                            current_date = line_date
                        continue

            candidate_pattern = scope["candidate_pattern"]
            if candidate_pattern and candidate_pattern.search(working_line):
                candidate_lines += 1

            line_pattern = scope["line_pattern"]
            match = line_pattern.match(working_line) if line_pattern else None
            if match:
                matched_starts += 1
                if current_match:
                    parsed = self._build_transaction(
                        current_match,
                        desc_lines,
                        account,
                        current_date,
                        statement_year,
                        statement_month,
                        scope["amount_sign"],
                        scope["sign_rules"],
                        current_scope_for_match,
                    )
                    if parsed and self._scope_is_selected(parsed, selected_scope_ids):
                        transactions.append(parsed)
                if line_date:
                    current_date = line_date
                current_match = match
                desc_lines = []
                current_scope_for_match = dict(current_scope) if current_scope else None
                continue

            if line_date:
                current_date = line_date

            if current_match and scope["multiline"]:
                desc_lines.append(clean_text(working_line))

        if current_match:
            parsed = self._build_transaction(
                current_match,
                desc_lines,
                account,
                current_date,
                statement_year,
                statement_month,
                scope["amount_sign"],
                scope["sign_rules"],
                current_scope_for_match,
            )
            if parsed and self._scope_is_selected(parsed, selected_scope_ids):
                transactions.append(parsed)

        return transactions, {
            "name": scope["name"],
            "matched_starts": matched_starts,
            "candidate_lines": candidate_lines,
            "transactions_found": len(transactions),
            "stop_reason": stop_reason,
        }

    def _build_transaction(
        self,
        match: re.Match[str],
        desc_lines: List[str],
        account: str,
        current_date: Optional[str],
        statement_year: Optional[int],
        statement_month: Optional[int],
        amount_sign: str,
        sign_rules: Dict[str, Any],
        active_scope: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        groups = match.groupdict()
        date_field = self.fields.get("date", "date")
        date_str = groups.get(date_field, "") or current_date or ""
        description = self._build_description(groups)
        if desc_lines:
            description = clean_text(f"{description} {' '.join(desc_lines)}")

        amount_str = groups.get(self.fields.get("amount", "amount"), "")
        balance_key = self.fields.get("balance", "balance")
        balance_str = groups.get(balance_key, "") if balance_key else ""

        parsed_date = self._parse_spec_date(date_str, statement_year, statement_month)
        if not parsed_date or not description or not amount_str:
            return None

        amount = parse_amount(amount_str)
        amount = self._apply_amount_sign(amount, amount_sign, sign_rules, groups)

        balance: Any = ""
        if balance_str:
            balance = parse_amount(balance_str)

        currency_key = self.fields.get("currency", "currency")
        currency_str = groups.get(currency_key, "") if currency_key else ""
        currency_map = {str(key).upper(): str(value) for key, value in self.normalize.get("currency_map", {}).items()}
        currency_value = currency_map.get(currency_str.strip().upper(), currency_str.strip().upper()) if currency_str else ""

        transaction = {
            "date": parsed_date,
            "description": description,
            "amount": amount,
            "balance": balance,
            "account": account,
            "bank": self.display_name,
            "currency": currency_value or self.currency_default,
            "transaction_type": "Credit" if amount > 0 else "Debit",
        }
        if active_scope:
            transaction["account"] = active_scope.get("account") or transaction["account"]
            if not currency_value:
                transaction["currency"] = active_scope.get("currency") or transaction["currency"]
            transaction["scope_id"] = active_scope.get("id", "")
            transaction["scope_label"] = active_scope.get("label", "")
            transaction["product_type"] = active_scope.get("product_type", "")
            if active_scope.get("linked_account"):
                transaction["linked_account"] = active_scope["linked_account"]
        return transaction

    def _scope_is_selected(self, transaction: Dict[str, Any], selected_scope_ids: Optional[List[str]]) -> bool:
        if not selected_scope_ids:
            return True
        scope_id = transaction.get("scope_id", "")
        if not scope_id:
            return not self.supports_explicit_scopes
        return scope_id in selected_scope_ids

    def _build_description(self, groups: Dict[str, str]) -> str:
        template = self.fields.get("description_template", "")
        if template:
            values = {key: groups.get(key, "") for key in groups}
            return clean_text(template.format(**values))
        return clean_text(groups.get(self.fields.get("description", "description"), ""))

    def _apply_amount_sign(
        self,
        amount: float,
        amount_sign: str,
        sign_rules: Dict[str, Any],
        groups: Dict[str, str],
    ) -> float:
        if amount_sign == "positive":
            return abs(amount)
        if amount_sign == "negative":
            return -abs(amount)
        if amount_sign != "rule_based":
            return amount

        field_name = sign_rules.get("field", "")
        raw_value = str(groups.get(field_name, "")).strip()
        if not raw_value:
            return amount

        explicit_debits = set(sign_rules.get("debit_codes", []))
        explicit_credits = set(sign_rules.get("credit_codes", []))
        prefix_defaults = sign_rules.get("prefix_defaults", {})
        prefix_credit_overrides = sign_rules.get("prefix_credit_overrides", {})
        prefix_debit_overrides = sign_rules.get("prefix_debit_overrides", {})

        if raw_value in explicit_debits:
            return -abs(amount)
        if raw_value in explicit_credits:
            return abs(amount)

        numeric_part = raw_value.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        prefix = numeric_part[0] if numeric_part else ""
        if prefix:
            if raw_value in prefix_credit_overrides.get(prefix, []):
                return abs(amount)
            if raw_value in prefix_debit_overrides.get(prefix, []):
                return -abs(amount)
            if prefix_defaults.get(prefix) == "credit":
                return abs(amount)
            if prefix_defaults.get(prefix) == "debit":
                return -abs(amount)

        default_sign = sign_rules.get("default", "debit")
        if default_sign == "credit":
            return abs(amount)
        if default_sign == "debit":
            return -abs(amount)
        return amount

    def _parse_spec_date(
        self,
        date_str: str,
        statement_year: Optional[int],
        statement_month: Optional[int],
    ) -> Optional[str]:
        if not date_str:
            return None

        normalized_date = self._normalize_date_str(date_str)

        for fmt in self.date_formats:
            try:
                parsed_date = datetime.strptime(normalized_date, fmt)
                if parsed_date.year == 1900 and statement_year:
                    inferred_year = statement_year
                    if statement_month and parsed_date.month > statement_month:
                        inferred_year -= 1
                    parsed_date = parsed_date.replace(year=inferred_year)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return parse_date(date_str)

    def _extract_statement_year(self, text: str) -> Optional[int]:
        if not self.statement_year_regex:
            return None

        match = self.statement_year_regex.search(text)
        if not match:
            return None

        for group_name in ("year", 1):
            try:
                year = match.group(group_name)
            except IndexError:
                continue
            except KeyError:
                continue
            if year:
                return int(year)

        return None

    def _extract_statement_month(self, text: str) -> Optional[int]:
        if not self.statement_month_regex:
            return None

        match = self.statement_month_regex.search(text)
        if not match:
            return None

        for group_name in ("month", 1):
            try:
                raw_month = match.group(group_name)
            except IndexError:
                continue
            except KeyError:
                continue
            if raw_month:
                normalized = self._normalize_date_str(str(raw_month))
                for fmt in ("%b", "%m"):
                    try:
                        return datetime.strptime(normalized, fmt).month
                    except ValueError:
                        continue

        return None

    def _normalize_date_str(self, value: str) -> str:
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

        normalized = value
        for source, target in month_aliases.items():
            normalized = re.sub(source, target, normalized, flags=re.IGNORECASE)
        return normalized

    def _extract_roela_columns_text(self, file_path: str) -> str:
        if pdfplumber is None:
            return ""

        header_cut = float(self.pdf_text_options.get("header_cut", 260.0))
        footer_cut = float(self.pdf_text_options.get("footer_cut", 30.0))
        split_ratio = float(self.pdf_text_options.get("split_ratio", 0.515))
        margin_pt = float(self.pdf_text_options.get("margin_pt", 0.0))
        stop_keyword = str(self.pdf_text_options.get("stop_keyword", "DE INTERES PARA USTED")).upper()

        pages_text: List[str] = []
        try:
            with pdfplumber.open(file_path) as pdf:
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text() or ""
                    if first_page_text and self.account_regex:
                        account_match = self.account_regex.search(first_page_text)
                        if account_match:
                            pages_text.append(f"Cuenta {account_match.group(1)}")

                for page in pdf.pages:
                    full_text = page.extract_text() or ""
                    if stop_keyword and stop_keyword in full_text.upper():
                        break

                    try:
                        y0 = header_cut
                        y1 = page.height - footer_cut
                        split_x = page.width * split_ratio
                        left_bbox = (0, y0, split_x - margin_pt, y1)
                        right_bbox = (split_x + margin_pt, y0, page.width, y1)
                        left_text = page.within_bbox(left_bbox).extract_text(x_tolerance=4, y_tolerance=2) or ""
                        right_text = page.within_bbox(right_bbox).extract_text(x_tolerance=4, y_tolerance=2) or ""
                        merged = (left_text + "\n" + right_text).strip()
                        if merged:
                            pages_text.append(merged)
                            continue
                    except Exception as exc:
                        self.logger.warning("Falling back to full-page Roela extraction for %s: %s", self.source_path, exc)

                    if full_text:
                        pages_text.append(full_text)
        except Exception as exc:
            self.logger.warning("Roela column extraction failed for %s: %s", self.source_path, exc)
            return ""

        return clean_text("\n".join(pages_text), preserve_lines=True)

    def _extract_x_band_table_text(self, file_path: str, original_text: str = "") -> str:
        if pdfplumber is None:
            return ""

        row_merge_tolerance = float(self.pdf_text_options.get("row_merge_tolerance", 1.5))
        block_gap = float(self.pdf_text_options.get("block_gap", 10.0))
        date_max_x = float(self.pdf_text_options.get("date_max_x", 75.0))
        description_min_x = float(self.pdf_text_options.get("description_min_x", 75.0))
        description_max_x = float(self.pdf_text_options.get("description_max_x", 210.0))
        operation_min_x = float(self.pdf_text_options.get("operation_min_x", 210.0))
        operation_max_x = float(self.pdf_text_options.get("operation_max_x", 290.0))
        amount_min_x = float(self.pdf_text_options.get("amount_min_x", 290.0))
        amount_max_x = float(self.pdf_text_options.get("amount_max_x", 360.0))
        balance_min_x = float(self.pdf_text_options.get("balance_min_x", 360.0))
        balance_max_x = float(self.pdf_text_options.get("balance_max_x", 430.0))
        date_pattern = re.compile(str(self.pdf_text_options.get("date_pattern", r"^\d{2}-\d{2}-\d{4}$")))
        trailing_operation_pattern = re.compile(
            str(self.pdf_text_options.get("trailing_operation_pattern", r"^(?P<description>.+?)\s*(?P<operation_id>\d{9,15})$"))
        )
        keep_text_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.pdf_text_options.get("keep_text_patterns", [])
        ]
        ignore_text_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.pdf_text_options.get("ignore_text_patterns", [])
        ]

        def parse_row(words: List[Dict[str, Any]]) -> Dict[str, str]:
            bands = {
                "date": [],
                "description": [],
                "operation": [],
                "amount": [],
                "balance": [],
            }
            for word in sorted(words, key=lambda item: item["x0"]):
                x0 = float(word["x0"])
                if x0 < date_max_x:
                    bands["date"].append(word["text"])
                elif description_min_x <= x0 < description_max_x:
                    bands["description"].append(word["text"])
                elif operation_min_x <= x0 < operation_max_x:
                    bands["operation"].append(word["text"])
                elif amount_min_x <= x0 < amount_max_x:
                    bands["amount"].append(word["text"])
                elif balance_min_x <= x0 < balance_max_x:
                    bands["balance"].append(word["text"])

            return {key: clean_text(" ".join(values)) for key, values in bands.items()}

        def flush_block(block_rows: List[Dict[str, Any]]) -> str:
            parsed_rows = [parse_row(row["words"]) for row in block_rows]
            anchor = next((row for row in parsed_rows if date_pattern.match(row["date"])), None)
            if anchor is None:
                return ""

            description = clean_text(" ".join(row["description"] for row in parsed_rows if row["description"]))
            if not description:
                return ""

            operation = anchor["operation"]
            trailing_match = trailing_operation_pattern.match(description)
            if trailing_match and not operation:
                description = clean_text(trailing_match.group("description"))
                operation = trailing_match.group("operation_id")

            amount = clean_text(anchor["amount"].replace("$", " "))
            balance = clean_text(anchor["balance"].replace("$", " "))
            if not anchor["date"] or not description or not operation or not amount or not balance:
                return ""

            return clean_text(
                f"{anchor['date']} {description} {operation} {amount} {balance}",
                preserve_lines=False,
            )

        prepared_lines: List[str] = []
        seen_lines: set[str] = set()
        if original_text and keep_text_patterns:
            for line in original_text.splitlines():
                cleaned_line = clean_text(line)
                if not cleaned_line:
                    continue
                if any(pattern.search(cleaned_line) for pattern in keep_text_patterns):
                    if cleaned_line not in seen_lines:
                        prepared_lines.append(cleaned_line)
                        seen_lines.add(cleaned_line)

        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
                    if not words:
                        continue

                    grouped_rows: List[Dict[str, Any]] = []
                    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
                        if grouped_rows and abs(float(word["top"]) - grouped_rows[-1]["top"]) <= row_merge_tolerance:
                            grouped_rows[-1]["words"].append(word)
                        else:
                            grouped_rows.append({"top": float(word["top"]), "words": [word]})

                    current_block: List[Dict[str, Any]] = []
                    for row in grouped_rows:
                        if current_block and abs(row["top"] - current_block[-1]["top"]) > block_gap:
                            line = flush_block(current_block)
                            if line and not any(pattern.search(line) for pattern in ignore_text_patterns):
                                prepared_lines.append(line)
                            current_block = []
                        current_block.append(row)

                    if current_block:
                        line = flush_block(current_block)
                        if line and not any(pattern.search(line) for pattern in ignore_text_patterns):
                            prepared_lines.append(line)
        except Exception as exc:
            self.logger.warning("x-band table extraction failed for %s: %s", self.source_path, exc)
            return ""

        return clean_text("\n".join(prepared_lines), preserve_lines=True)


class FormatRegistry:
    def __init__(self, root: Path | None = None):
        self.root = root or SPEC_ROOT
        self._cache: Optional[List[FormatSpec]] = None

    def refresh(self) -> None:
        self._cache = None

    def all_specs(self) -> List[FormatSpec]:
        if self._cache is not None:
            return self._cache

        specs: List[FormatSpec] = []
        if not self.root.exists():
            self._cache = specs
            return specs

        for spec_path in sorted(self.root.glob("*/*/spec.toml")):
            specs.append(FormatSpec(spec_path, _load_toml(spec_path)))

        self._cache = specs
        return specs

    def specs_by_status(self, status: str) -> List[FormatSpec]:
        return [spec for spec in self.all_specs() if spec.status == status]

    def has_published_bank(self, bank_id: str) -> bool:
        return any(spec.bank_id == bank_id for spec in self.specs_by_status("published"))

    def get_published_spec(self, bank_id: str, format_id: str) -> Optional[FormatSpec]:
        for spec in self.specs_by_status("published"):
            if spec.bank_id == bank_id and spec.format_id == format_id:
                return spec
        return None

    def get_spec(self, bank_id: str, format_id: str) -> Optional[FormatSpec]:
        for spec in self.all_specs():
            if spec.bank_id == bank_id and spec.format_id == format_id:
                return spec
        return None

    def match_published(self, text: str, bank_hint: Optional[str] = None) -> Optional[SpecMatch]:
        candidates = self.specs_by_status("published")
        if bank_hint and bank_hint != "unknown":
            hinted = [spec for spec in candidates if spec.bank_id == bank_hint]
            if not hinted:
                return None
            candidates = hinted

        best_match: Optional[SpecMatch] = None
        for spec in candidates:
            match = spec.evaluate(text)
            if match.score < spec.min_score:
                continue
            if best_match is None or match.score > best_match.score:
                best_match = match
        return best_match

    def list_drafts(self) -> List[FormatSpec]:
        return self.specs_by_status("draft")


def load_expected_transactions(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
