import re
import fitz  # PyMuPDF — page rendering only
import pytesseract
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


_OSD_CONFIDENCE_THRESHOLD = 0.4  # below this, OSD rotation is unreliable


def _detect_rotation(img: Image.Image) -> int:
    """Use Tesseract OSD to detect how many degrees to rotate the image counter-clockwise
    (PIL convention) to make text upright. Returns 0, 90, 180, or 270.

    Tesseract OSD "Rotate" is clockwise; PIL rotate() is counter-clockwise,
    so we convert: pil_angle = (360 - osd_angle) % 360.
    Only applies rotation when OSD orientation confidence >= _OSD_CONFIDENCE_THRESHOLD.
    Falls back to 0 on failure or low confidence.
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
    """Render page to image at 2x zoom (~144 DPI), correct rotation if needed,
    and run Tesseract OCR.

    Returns extracted text. confidence_floor kept for API compatibility but
    Tesseract filters low-confidence words internally.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()

    rotation = _detect_rotation(img)
    if rotation != 0:
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
