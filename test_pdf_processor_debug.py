from pdf_processor import PDFProcessor

class DummyProcessor(PDFProcessor):
    def _extract_text_from_pdf(self, file_path, debug_log=None):
        if debug_log is not None:
            debug_log.append("dummy extractor")
        return "dummy text"

    def _detect_bank(self, text):
        return "chase"


def test_process_pdf_debug():
    proc = DummyProcessor()
    parser = proc.parser_factory.get_parser("chase")
    parser.parse_transactions = lambda text, filename: [
        {"date": "2024-01-01", "description": "desc", "amount": "1.00"}
    ]
    result = proc.process_pdf("dummy.pdf", "dummy.pdf", debug=True)
    assert result["success"]
    assert "debug_log" in result
    assert any("Finished text extraction" in msg for msg in result["debug_log"])
