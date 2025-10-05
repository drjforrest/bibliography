import fitz


def extract_text(file_path):
    doc = fitz.open(file_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        pages.append({"file": file_path, "page": i + 1, "text": text})
    return pages
