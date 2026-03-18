import io
import re
from pathlib import Path

import pytest
from openpyxl import load_workbook

from excel_generator import ExcelGenerator
from pdf_processor import PDFProcessor


BBVA_MULTI_SCOPE_PDF = Path("attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf")


def test_galicia_pdf_uses_declarative_spec():
    processor = PDFProcessor()
    result = processor.process_pdf("attached_assets/TestGalicia.pdf", "TestGalicia.pdf")

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["format_id"] == "default"
    assert result["bank_detected"] == "galicia_ar"
    assert result["total_transactions"] == 52
    assert "Consolidado de retención" not in result["transactions"][-1]["description"]
    assert "Los depósitos en pesos" not in result["transactions"][-1]["description"]


def test_roela_pdf_uses_declarative_spec_successfully():
    processor = PDFProcessor()
    result = processor.process_pdf("attached_assets/BancoRoela.Argentina.Test.pdf", "BancoRoela.Argentina.Test.pdf")

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["bank_detected"] == "roela_ar"
    assert result["format_id"] == "default"
    assert result["format_version"] == 1
    assert result["total_transactions"] >= 4900
    assert result["transactions"][0]["account"] == "22537/8"
    assert result["transactions"][5]["amount"] < 0


def test_chase_pdf_uses_declarative_spec_with_correct_dates_and_account():
    processor = PDFProcessor()
    result = processor.process_pdf("attached_assets/BANCO CH 2024 1.pdf", "BANCO CH 2024 1.pdf")

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["bank_detected"] == "chase"
    assert result["format_id"] == "default"
    assert result["format_version"] == 1
    assert result["total_transactions"] == 12
    assert result["transactions"][0]["date"] == "2024-01-02"
    assert result["transactions"][4]["date"] == "2024-01-03"
    assert result["transactions"][0]["account"] == "000000771927196"


def test_chase_second_pdf_matches_same_published_spec():
    processor = PDFProcessor()
    result = processor.process_pdf("attached_assets/BANCO CH 2024 2.pdf", "BANCO CH 2024 2.pdf")

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["bank_detected"] == "chase"
    assert result["format_id"] == "default"
    assert result["total_transactions"] == 10
    assert result["transactions"][0]["date"] == "2024-02-05"
    assert result["transactions"][0]["account"] == "000000771927196"


@pytest.mark.skipif(not BBVA_MULTI_SCOPE_PDF.exists(), reason="BBVA consolidated sample is not available in this workspace")
def test_bbva_pdf_analysis_reports_multiple_scopes():
    processor = PDFProcessor()
    result = processor.analyze_pdf(
        "attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf",
        "01-2023 BBVA.pdf",
    )

    assert result["success"] is True
    assert result["bank_detected"] == "bbva"
    assert result["format_id"] == "default"
    assert result["multi_scope"] is True
    assert len(result["available_scopes"]) == 5


def test_bbva_account_summary_pdf_uses_new_single_scope_spec():
    processor = PDFProcessor()
    analysis = processor.analyze_pdf(
        "attached_assets/nuevo_formato/BBVA/Resumen caja de ahorro BBVA 09-2023.pdf",
        "Resumen caja de ahorro BBVA 09-2023.pdf",
    )
    result = processor.process_pdf(
        "attached_assets/nuevo_formato/BBVA/Resumen caja de ahorro BBVA 09-2023.pdf",
        "Resumen caja de ahorro BBVA 09-2023.pdf",
    )

    assert analysis["success"] is True
    assert analysis["bank_detected"] == "bbva"
    assert analysis["format_id"] == "account_summary"
    assert analysis["multi_scope"] is False
    assert len(analysis["available_scopes"]) == 1
    assert analysis["available_scopes"][0]["label"] == "CA $ 354-428727/2"

    assert result["success"] is True
    assert result["parse_status"] == "ok"
    assert result["bank_detected"] == "bbva"
    assert result["format_id"] == "account_summary"
    assert result["format_version"] == 1
    assert result["total_transactions"] == 12
    assert result["transactions"][0]["date"] == "2023-08-22"
    assert result["transactions"][0]["amount"] == 71093.08
    assert result["transactions"][-1]["description"] == "CUENTA VISA NRO. 79083794696899"
    assert all(transaction["scope_label"] == "CA $ 354-428727/2" for transaction in result["transactions"])


@pytest.mark.skipif(not BBVA_MULTI_SCOPE_PDF.exists(), reason="BBVA consolidated sample is not available in this workspace")
def test_bbva_pdf_can_extract_only_bank_accounts():
    processor = PDFProcessor()
    analysis = processor.analyze_pdf(
        "attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf",
        "01-2023 BBVA.pdf",
    )
    selected_scope_ids = [
        scope["id"]
        for scope in analysis["available_scopes"]
        if scope["product_type"] == "bank_account"
    ]
    result = processor.process_pdf(
        "attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf",
        "01-2023 BBVA.pdf",
        selected_scope_ids=selected_scope_ids,
    )

    assert result["success"] is True
    assert result["multi_scope"] is True
    assert result["transactions"]
    assert all(transaction["product_type"] == "bank_account" for transaction in result["transactions"])
    assert any(transaction["scope_label"] == "CA $ 354-428727/2" for transaction in result["transactions"])
    assert any(transaction["scope_label"] == "CC $ 354-560404/1" for transaction in result["transactions"])


@pytest.mark.skipif(not BBVA_MULTI_SCOPE_PDF.exists(), reason="BBVA consolidated sample is not available in this workspace")
def test_bbva_pdf_can_extract_only_credit_card_scope():
    processor = PDFProcessor()
    analysis = processor.analyze_pdf(
        "attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf",
        "01-2023 BBVA.pdf",
    )
    credit_scope = next(scope for scope in analysis["available_scopes"] if scope["product_type"] == "credit_card")
    result = processor.process_pdf(
        "attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf",
        "01-2023 BBVA.pdf",
        selected_scope_ids=[credit_scope["id"]],
    )

    assert result["success"] is True
    assert result["transactions"]
    assert all(transaction["scope_id"] == credit_scope["id"] for transaction in result["transactions"])
    assert all(transaction["product_type"] == "credit_card" for transaction in result["transactions"])


@pytest.mark.skipif(not BBVA_MULTI_SCOPE_PDF.exists(), reason="BBVA consolidated sample is not available in this workspace")
def test_bbva_multi_scope_excel_generation_succeeds():
    processor = PDFProcessor()
    analysis = processor.analyze_pdf(
        "attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf",
        "01-2023 BBVA.pdf",
    )
    selected_scope_ids = [scope["id"] for scope in analysis["available_scopes"]]
    result = processor.process_pdf(
        "attached_assets/nuevo_formato/BBVA/01-2023 BBVA.pdf",
        "01-2023 BBVA.pdf",
        selected_scope_ids=selected_scope_ids,
    )

    summary = {
        "total_files": 1,
        "successful_files": 1,
        "failed_files": 0,
        "total_transactions": result["total_transactions"],
        "banks_detected": {result["bank_name"]},
        "errors": [],
        "selected_scopes": analysis["available_scopes"],
    }
    workbook_bytes = ExcelGenerator().create_excel_file(result["transactions"], summary)
    workbook = load_workbook(io.BytesIO(workbook_bytes))
    scope_sheet_names = [
        name
        for name in workbook.sheetnames
        if name not in {"Summary", "All Transactions", "Analysis", "Monthly Summary"}
    ]

    assert result["success"] is True
    assert "Summary" in workbook.sheetnames
    assert "All Transactions" in workbook.sheetnames
    assert scope_sheet_names
    assert all(re.search(r'[:\\\\/?*\\[\\]]', name) is None for name in workbook.sheetnames)
