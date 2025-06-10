class Page:
    def extract_text(self):
        return ""

class PdfReader:
    def __init__(self, file, *args, **kwargs):
        self.pages = [Page()]
