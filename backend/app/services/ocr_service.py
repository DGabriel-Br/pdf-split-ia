import logging
import re
import fitz  # PyMuPDF — page rendering only
import pytesseract
from PIL import Image
import io
from app.config import get_settings

log = logging.getLogger(__name__)

_OSD_CONFIDENCE_THRESHOLD = 0.4

# Apply tesseract_cmd from settings if configured; otherwise rely on system PATH.
_cmd = get_settings().tesseract_cmd
if _cmd:
    pytesseract.pytesseract.tesseract_cmd = _cmd


def _detect_rotation(img: Image.Image) -> int:
    """Use Tesseract OSD to detect how many degrees to rotate counter-clockwise (PIL convention).

    Tesseract OSD "Rotate" is clockwise; PIL rotate() is counter-clockwise,
    so: pil_angle = (360 - osd_angle) % 360.
    Only applies rotation when OSD confidence >= _OSD_CONFIDENCE_THRESHOLD.
    """
    try:
        osd = pytesseract.image_to_osd(img, config="--psm 0 -c min_characters_to_try=5")
        m_rot  = re.search(r"Rotate: (\d+)", osd)
        m_conf = re.search(r"Orientation confidence: ([0-9.]+)", osd)
        if not m_rot:
            return 0
        confidence = float(m_conf.group(1)) if m_conf else 0.0
        if confidence < _OSD_CONFIDENCE_THRESHOLD:
            return 0
        osd_angle = int(m_rot.group(1))
        return (360 - osd_angle) % 360
    except Exception:
        return 0


def ocr_page(pdf_path: str, page_index: int, confidence_floor: float = 0.4) -> str:
    """Render page to image at 2x zoom (~144 DPI), correct rotation, and run Tesseract OCR."""
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_index]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
    finally:
        doc.close()

    rotation = _detect_rotation(img)
    if rotation != 0:
        log.debug("Pagina %d: rotacionada %d graus (PIL)", page_index + 1, rotation)
        img = img.rotate(rotation, expand=True)

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
