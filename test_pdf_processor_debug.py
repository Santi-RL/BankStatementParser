import pytest
from pdf_processor import PDFProcessor

class DummyProcessor(PDFProcessor):
    def _extract_text_from_pdf(self, file_path, debug_log=None):
        # Simulate text extraction and record debug step
        if debug_log is not None:
            debug_log.append("dummy extractor")
        return "dummy text"

    def _detect_bank(self, text_content):
        # Always detect 'chase' for testing
        return "chase"


def test_process_pdf_debug():
    # Prepare processor and override parser behavior
    proc = DummyProcessor()
    parser = proc.parser_factory.get_parser("chase")
    parser.parse_transactions = lambda text, filename: [
        {"date": "2024-01-01", "description": "desc", "amount": "1.00"}
    ]

    # Execute with debug enabled
    result = proc.process_pdf("dummy.pdf", "dummy.pdf", debug=True)

    # Assertions
    assert result["success"] is True
    assert "debug_log" in result

    debug_log = result["debug_log"]
    # Check that our dummy extractor step was recorded
    assert "dummy extractor" in debug_log
    # Check key debug messages are present
    assert any("Finished text extraction" in msg for msg in debug_log)
    assert any("Detected bank:" in msg for msg in debug_log)
    assert any("Parsed 1 transactions" in msg for msg in debug_log)
    assert any("Validation complete, 1 valid transactions" in msg for msg in debug_log)
