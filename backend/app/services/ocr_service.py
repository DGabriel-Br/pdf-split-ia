import logging
import re
import fitz  # PyMuPDF — page rendering only
import pytesseract
from PIL import Image
import io
from app.config import get_settings

log = logging.getLogger(__name__)

# Apply tesseract_cmd from settings if configured; otherwise rely on system PATH.
_cmd = get_settings().tesseract_cmd
if _cmd:
    pytesseract.pytesseract.tesseract_cmd = _cmd


def _detect_rotation(img: Image.Image) -> int:
    """Use Tesseract OSD to detect rotation angle (PIL convention: counter-clockwise degrees).
    Returns the suggested angle without confidence filtering; text comparison in the caller verifies.
    Tesseract OSD "Rotate" is clockwise; PIL rotate() is counter-clockwise: pil = (360 - osd) % 360."""
    try:
        osd = pytesseract.image_to_osd(img, config="--psm 0 -c min_characters_to_try=5")
        m_rot = re.search(r"Rotate: (\d+)", osd)
        if not m_rot:
            return 0
        osd_angle = int(m_rot.group(1))
        return (360 - osd_angle) % 360
    except Exception:
        return 0


def _run_ocr(img: Image.Image, confidence_floor: float) -> str:
    data = pytesseract.image_to_data(
        img, lang="eng+por", config="--psm 6",
        output_type=pytesseract.Output.DICT,
    )
    threshold = confidence_floor * 100
    words = [
        word for word, conf in zip(data["text"], data["conf"])
        if word.strip() and int(conf) >= threshold
    ]
    return " ".join(words)


def ocr_page(pdf_path: str, page_index: int, confidence_floor: float = 0.4) -> str:
    """Render page to image at 2x zoom (~144 DPI), auto-correct rotation, and run Tesseract OCR."""
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_index]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
    finally:
        doc.close()

    text_original = _run_ocr(img, confidence_floor)
    osd_rotation = _detect_rotation(img)

    if osd_rotation != 0:
        # OSD suggested a rotation — verify with text comparison (5% threshold).
        text_rotated = _run_ocr(img.rotate(osd_rotation, expand=True), confidence_floor)
        if len(text_rotated) > len(text_original) * 1.05:
            log.debug(
                "Pagina %d: rotacionada %d graus (OSD: %d > %d chars)",
                page_index + 1, osd_rotation, len(text_rotated), len(text_original),
            )
            return text_rotated
        log.debug(
            "Pagina %d: OSD sugeriu %d graus mas rotacao nao melhorou (%d vs %d chars)",
            page_index + 1, osd_rotation, len(text_rotated), len(text_original),
        )
        return text_original

    # OSD returned 0 — try remaining angles as fallback for scans OSD missed
    best_text = text_original
    best_angle = 0
    for angle in (90, 270, 180):
        t = _run_ocr(img.rotate(angle, expand=True), confidence_floor)
        if len(t) > len(best_text):
            best_text = t
            best_angle = angle
    if best_angle != 0 and len(best_text) > len(text_original) * 1.05:
        log.debug(
            "Pagina %d: rotacionada %d graus (fallback OSD=0: %d > %d chars)",
            page_index + 1, best_angle, len(best_text), len(text_original),
        )
        return best_text
    return text_original
