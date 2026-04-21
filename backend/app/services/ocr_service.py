import fitz  # PyMuPDF — page rendering only
import pytesseract
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def ocr_page(pdf_path: str, page_index: int, confidence_floor: float = 0.4) -> str:
    """Render page to image at 2x zoom (~144 DPI) and run Tesseract OCR.

    Returns extracted text. confidence_floor kept for API compatibility but
    Tesseract filters low-confidence words internally.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()

    data = pytesseract.image_to_data(
        img, lang="eng+por", config="--psm 6",
        output_type=pytesseract.Output.DICT,
    )
    # Tesseract confidence is 0-100; map confidence_floor (0-1) to 0-100 scale
    threshold = confidence_floor * 100
    words = [
        word for word, conf in zip(data["text"], data["conf"])
        if word.strip() and int(conf) >= threshold
    ]
    return " ".join(words)
