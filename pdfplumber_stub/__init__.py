class Page:
    def extract_text(self):
        return ""

class PDF:
    def __init__(self, *args, **kwargs):
        self.pages = [Page()]
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass

def open(file_path):
    return PDF()
