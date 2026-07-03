#!/usr/bin/env python3
"""Diagnostic script for the published Chase declarative spec."""

from __future__ import annotations

from pathlib import Path
import sys
import tomllib

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from format_engine import FormatSpec  # noqa: E402


TEST_CONTENT = """
December 30, 2023 through January 31, 2024
JPMorgan Chase Bank, N.A.

DEPOSITS AND ADDITIONS

     DATE                      DESCRIPTION                                                                                                          AMOUNT
01/02                          Deposit    2063844249                                                                                               $300.00
01/02                          Zelle Payment From Dave Adden Pinnock 19468032866                                                                   1,800.00
01/18                          Deposit    2096126287                                                                                               2,000.00
01/26                          Zelle Payment From Osvaldo Mario Mastino 19679532458                                                                 110.00

Total Deposits and Additions                                                                                                                  $4,210.00

ELECTRONIC WITHDRAWALS

     DATE                          DESCRIPTION                                                                                                                       AMOUNT
01/03                              Zelle Payment To Ugarte Martin Jpm99A7Fueo0                                                                                       $500.00
01/04                              Zelle Payment To Herby 1 Jpm99A7Hl7Mx                                                                                              400.00
01/08                              Zelle Payment To Laura Coll 19516915865                                                                                            700.00

Total Electronic Withdrawals                                                                                                                                    $1,600.00

FEES

     DATE                          DESCRIPTION                                                                                                                       AMOUNT
01/31                              Monthly Service Fee                                                                                                                $15.00

Total Fees                                                                                                                                                            $15.00
"""


def main() -> int:
    spec_path = PROJECT_ROOT / "parser_specs" / "chase" / "default" / "spec.toml"
    with spec_path.open("rb") as handle:
        spec = FormatSpec(spec_path, tomllib.load(handle))

    result = spec.parse_transactions(TEST_CONTENT)
    print(f"Found {len(result.transactions)} transactions")
    print(f"Passes change detection: {result.passes_change_detection}")
    print(f"Diagnostics: {result.diagnostics}")
    for index, transaction in enumerate(result.transactions, 1):
        print(f"{index}. {transaction['date']} - {transaction['description']} - {transaction['amount']}")

    return 0 if result.transactions else 1


if __name__ == "__main__":
    raise SystemExit(main())
