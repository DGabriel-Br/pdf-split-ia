import pdfplumber


def extract_page_text(pdf_path: str, page_index: int) -> tuple[str, int]:
    """Extract text from a single page (0-based index).

    Returns (text, char_count). char_count == 0 means scanned/image-only page.
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
        text = text.strip()
        return text, len(text)


def get_page_count(pdf_path: str) -> int:
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)
