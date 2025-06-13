from pdf_processor import PDFProcessor

if __name__ == "__main__":
    pdf_path = input("Introduce la ruta del archivo PDF: ")
    processor = PDFProcessor()
    texto = processor._extract_text_from_pdf(pdf_path)
    print(texto)