import logging
import pdfplumber

log = logging.getLogger(__name__)


def extract_page_text(pdf_path: str, page_index: int) -> tuple[str, int]:
    """Extract text from a single page (0-based index).

    Returns (text, char_count). char_count == 0 means scanned/image-only page.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_index >= len(pdf.pages):
                log.warning("Indice de pagina %d fora dos limites (total: %d)", page_index, len(pdf.pages))
                return "", 0
            page = pdf.pages[page_index]
            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            text = text.strip()
            return text, len(text)
    except Exception as exc:
        log.warning("Falha ao extrair texto da pagina %d: %s", page_index, exc)
        return "", 0


def extract_all_page_texts(pdf_path: str) -> list[tuple[str, int]]:
    """Open the PDF once and extract text from every page.

    Returns a list of (text, char_count) tuples, one per page.
    """
    results: list[tuple[str, int]] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                    text = text.strip()
                    results.append((text, len(text)))
                except Exception as exc:
                    log.warning("Falha ao extrair texto de pagina: %s", exc)
                    results.append(("", 0))
    except Exception as exc:
        log.warning("Falha ao abrir PDF para extracao em lote: %s", exc)
    return results


def get_page_count(pdf_path: str) -> int:
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)
