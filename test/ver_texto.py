import pdfplumber

with pdfplumber.open("BANCO CH 2024 1.pdf") as pdf:
    for i, page in enumerate(pdf.pages, start=1):
        print(f"\n--- Página {i} ---\n")
        text = page.extract_text()
        if text:
            print(text)
        else:
            print("[Sin texto extraído]")
