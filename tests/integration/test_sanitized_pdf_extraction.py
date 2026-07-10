from pathlib import Path
import re

import pytest

from pdf_processor import PDFProcessor
from tests.pdf_factory import create_positioned_text_pdf, create_text_pdf


SANITIZED_TEXT_PDF_CASES = [
    pytest.param(
        Path("parser_specs/galicia_ar/default/fixtures/sample_text.txt"),
        "galicia_ar",
        "default",
        3,
        id="galicia",
    ),
    pytest.param(
        Path("parser_specs/chase/default/fixtures/sample_text.txt"),
        "chase",
        "default",
        12,
        id="chase",
    ),
    pytest.param(
        Path("parser_specs/bbva/account_summary/fixtures/sample_text.txt"),
        "bbva",
        "account_summary",
        12,
        id="bbva_account_summary",
    ),
    pytest.param(
        Path("parser_specs/brubank/default/fixtures/sample_text.txt"),
        "brubank",
        "default",
        34,
        id="brubank",
    ),
]


@pytest.mark.parametrize(
    ("fixture_path", "expected_bank", "expected_format", "expected_transactions"),
    SANITIZED_TEXT_PDF_CASES,
)
def test_generated_sanitized_pdf_exercises_text_extraction(
    tmp_path,
    fixture_path,
    expected_bank,
    expected_format,
    expected_transactions,
):
    pdf_path = create_text_pdf(
        fixture_path.read_text(encoding="utf-8"),
        tmp_path / f"{expected_bank}-{expected_format}.pdf",
    )

    result = PDFProcessor().process_pdf(str(pdf_path), pdf_path.name)

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["bank_detected"] == expected_bank
    assert result["format_id"] == expected_format
    assert result["total_transactions"] == expected_transactions


def test_generated_roela_pdf_exercises_column_extraction(tmp_path):
    fixture_path = Path("parser_specs/roela_ar/default/fixtures/sample_text.txt")
    lines = [line for line in fixture_path.read_text(encoding="utf-8").splitlines() if line]
    pages = [
        [
            (50, 510 - index * 10, line, 7)
            for index, line in enumerate(lines[start:start + 45])
        ]
        for start in range(0, len(lines), 45)
    ]
    pdf_path = create_positioned_text_pdf(pages, tmp_path / "roela-columns.pdf")

    result = PDFProcessor().process_pdf(str(pdf_path), pdf_path.name)

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["bank_detected"] == "roela_ar"
    assert result["format_id"] == "default"
    assert result["total_transactions"] == 55


def test_generated_mercado_pago_pdf_exercises_x_band_extraction(tmp_path):
    fixture_path = Path("parser_specs/mercado_pago/default/fixtures/sample_text.txt")
    lines = [line for line in fixture_path.read_text(encoding="utf-8").splitlines() if line]
    line_pattern = re.compile(
        r"^(?P<date>\d{2}-\d{2}-\d{4})\s+"
        r"(?P<description>.+?)\s+"
        r"(?P<operation_id>\d{9,15})\s+"
        r"(?P<amount>-?[\d.]+,\d{2})\s+"
        r"(?P<balance>-?[\d.]+,\d{2})$"
    )
    items = [
        (40, 780 - index * 12, line, 8)
        for index, line in enumerate(lines[:4])
    ]
    for index, line in enumerate(lines[4:]):
        match = line_pattern.match(line)
        assert match is not None
        y = 700 - index * 20
        items.extend(
            [
                (40, y, match.group("date"), 5),
                (76, y, match.group("description"), 4.5),
                (220, y, match.group("operation_id"), 5),
                (300, y, match.group("amount"), 5),
                (370, y, match.group("balance"), 5),
            ]
        )
    pdf_path = create_positioned_text_pdf([items], tmp_path / "mercado-pago-x-bands.pdf")

    result = PDFProcessor().process_pdf(str(pdf_path), pdf_path.name)

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["bank_detected"] == "mercado_pago"
    assert result["format_id"] == "default"
    assert result["total_transactions"] == 11
