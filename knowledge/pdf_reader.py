import fitz


class PDFReader:

    def extract_text(self, file_path):

        document = fitz.open(file_path)

        text = ""

        for page in document:
            text += page.get_text()

        return text