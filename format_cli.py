from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from format_engine import FormatSpec
from format_training import (
    build_initial_spec,
    extract_text_from_pdf,
    publish_spec,
    regress_published_specs,
    save_draft,
    validate_spec,
    validate_spec_identifier,
)


def _load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _spec_identifier_arg(field_name: str):
    def parse(value: str) -> str:
        try:
            return validate_spec_identifier(field_name, value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from exc

    return parse


def _update_spec_from_args(spec: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    spec["meta"]["status"] = "draft"
    if args.required_keyword:
        spec["detect"]["required_keywords"] = args.required_keyword
    if args.excluded_keyword:
        spec["detect"]["excluded_keywords"] = args.excluded_keyword
    if args.line_pattern:
        spec["extract"]["line_pattern"] = args.line_pattern
    if args.candidate_pattern:
        spec["extract"]["candidate_pattern"] = args.candidate_pattern
    if args.section_start:
        spec["extract"]["section_start_patterns"] = args.section_start
    if args.ignore_pattern:
        spec["extract"]["ignore_patterns"] = args.ignore_pattern
    if args.stop_pattern:
        spec["extract"]["stop_patterns"] = args.stop_pattern
    if args.account_pattern is not None:
        spec["fields"]["account_pattern"] = args.account_pattern
    return spec


def command_train(args: argparse.Namespace) -> int:
    text = extract_text_from_pdf(args.pdf)
    spec = build_initial_spec(
        bank_id=args.bank_id,
        format_id=args.format_id,
        display_name=args.display_name,
        country=args.country,
        currency_default=args.currency,
        extracted_text=text,
    )
    spec = _update_spec_from_args(spec, args)
    working_text = FormatSpec(Path("preview/spec.toml"), spec).prepare_text(text, args.pdf)
    spec_path = save_draft(spec, working_text, [])
    print(spec_path)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    if args.pdf:
        text = extract_text_from_pdf(args.pdf)
    else:
        text = _load_text(args.text)
    transactions, diagnostics, ok = validate_spec(Path(args.spec), text, pdf_path=args.pdf)
    print(json.dumps({
        "ok": ok,
        "diagnostics": diagnostics,
        "transactions": len(transactions),
        "available_scopes": diagnostics.get("available_scopes", []),
    }, indent=2))
    return 0 if ok else 1


def command_publish(args: argparse.Namespace) -> int:
    path = publish_spec(Path(args.spec))
    print(path)
    return 0


def command_regress(_: argparse.Namespace) -> int:
    result = regress_published_specs()
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Declarative parser spec workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="Create a draft spec from a PDF")
    train_parser.add_argument("pdf", help="PDF sample path")
    train_parser.add_argument("--bank-id", required=True, type=_spec_identifier_arg("bank_id"))
    train_parser.add_argument("--format-id", required=True, type=_spec_identifier_arg("format_id"))
    train_parser.add_argument("--display-name", required=True)
    train_parser.add_argument("--country", default="AR")
    train_parser.add_argument("--currency", default="ARS")
    train_parser.add_argument("--required-keyword", action="append")
    train_parser.add_argument("--excluded-keyword", action="append")
    train_parser.add_argument("--line-pattern")
    train_parser.add_argument("--candidate-pattern")
    train_parser.add_argument("--section-start", action="append")
    train_parser.add_argument("--ignore-pattern", action="append")
    train_parser.add_argument("--stop-pattern", action="append")
    train_parser.add_argument("--account-pattern")
    train_parser.set_defaults(func=command_train)

    validate_parser = subparsers.add_parser("validate-draft", help="Validate a draft spec")
    validate_parser.add_argument("spec", help="Path to spec.toml")
    validate_group = validate_parser.add_mutually_exclusive_group(required=True)
    validate_group.add_argument("--pdf")
    validate_group.add_argument("--text")
    validate_parser.set_defaults(func=command_validate)

    publish_parser = subparsers.add_parser("publish", help="Publish a draft spec")
    publish_parser.add_argument("spec", help="Path to spec.toml")
    publish_parser.set_defaults(func=command_publish)

    regress_parser = subparsers.add_parser("regress", help="Run published spec regressions")
    regress_parser.set_defaults(func=command_regress)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
