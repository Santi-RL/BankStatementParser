import os
import tempfile
import base64
import pytest

from pdf_processor import PDFProcessor

pdfplumber = pytest.importorskip("pdfplumber")
PyPDF2 = pytest.importorskip("PyPDF2")

# Minimal PDF containing 'Hello, world!'
PDF_BASE64 = (
    "JVBERi0xLjMKMSAwIG9iago8PAovVHlwZS9DYXRhbG9nCi9QYWdlcyAyIDAgUgo+PgplbmRvYm8K"
    "MiAwIG9iago8PAovVHlwZS9QYWdlcwovQ291bnQgMQovS2lkcyBbMyAwIFJdCj4+CmVuZG9iagoz"
    "IDAgb2JqCjw8Ci9UeXBlL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzky"
    "XQovQ29udGVudHMgNCAwIFIKL1Jlc291cmNlcyA8PAovRm9udCA8PAovRjEgNSAwIFIKPj4KPj4K"
    "Pj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCAxOSAKPj4Kc3RyZWFtCkJUCjcwIDUwIFQKKEhl"
    "bGxvLCBXb3JsZCkgVGoKRVQKZW5kc3RyZWFtCmVuZG9iago1IDAgb2JqCjw8Ci9UeXBlL0ZvbnQK"
    "/U3VidHlwZS9UeXBlMQovQmFzZUZvbnQvSGVsdmV0aWNhCj4+CmVuZG9iagp4cmVmCjAgNgowMTEw"
    "MDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDEwIDAwMDAwIG4gCjAwMDAwMDAwNjEgMDAwMDAgbiAK"
    "MDAwMDAwMDAxMTYgMDAwMDAgbiAKMDAwMDAwMDIxNyAwMDAwMCBuIAowMDAwMDAwMDMwMiAwMDAw"
    "MCBuIAp0cmFpbGVyCjw8Ci9Sb290IDEgMCBSCi9TaXplIDYKL0luZm8gOCAwIFIKL0lEIFs8ZDk5"
    "MGMzZTNjZTY5NmJiYmJhM2U3N2JiODIwYjIwYmUgZDk5MGMzZTNjZTY5NmJiYmJhM2U3N2JiODIw"
    "YjIwYj5dPgpzdGFydHhyZWYKNDMzCmlkZW5yZWYKNiAKJSVFT0Y="
)

def create_temp_pdf():
    data = base64.b64decode(PDF_BASE64)
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def test_extract_text_from_pdf():
    processor = PDFProcessor()
    pdf_path = create_temp_pdf()
    try:
        text = processor._extract_text_from_pdf(pdf_path)
        assert "Hello, world!" in text
    finally:
        os.remove(pdf_path)
