import contextlib
import io
import easyocr
import fitz  # PyMuPDF — page rendering only

_reader: easyocr.Reader | None = None


def get_reader() -> easyocr.Reader:
    """Lazy singleton — first call takes 5-15s to load model weights."""
    global _reader
    if _reader is None:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            _reader = easyocr.Reader(["en", "pt"], gpu=False, verbose=False)
    return _reader


def ocr_page(pdf_path: str, page_index: int, confidence_floor: float = 0.4) -> str:
    """Render page to image at 2x zoom (~144 DPI) and run EasyOCR.

    Returns joined text from words above the confidence floor.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
    img_bytes = pix.tobytes("png")
    doc.close()

    reader = get_reader()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        results = reader.readtext(img_bytes, detail=1, paragraph=False)
    words = [text for (_, text, conf) in results if conf >= confidence_floor]
    return " ".join(words)
