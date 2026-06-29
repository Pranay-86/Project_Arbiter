from knowledge.pdf_reader import PDFReader


class DocumentLoader:

    def __init__(self):

        self.pdf_reader = PDFReader()

    def load(self, file_path):

        if file_path.endswith(".pdf"):

            return self.pdf_reader.extract_text(file_path)

        raise ValueError("Unsupported document format")