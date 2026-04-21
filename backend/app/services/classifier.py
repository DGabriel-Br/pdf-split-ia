import httpx
from app.config import Settings
from app.models import DocumentType

INVOICE_SIGNALS = {"invoice", "amount", "rate", "usd", "eur", "total", "payment", "unit price", "subtotal"}
PACKING_SIGNALS = {"packing list", "gross weight", "net weight", "cbm", "pieces", "carton", "dimensions", "n.w.", "g.w."}

PROMPT_TEMPLATE = """\
You are a document classification engine for import trade documents.
Analyze the page text and reply with EXACTLY TWO words separated by a space.

Word 1 — Document type:
  INVOICE       - primary purpose is financial settlement: itemized unit prices that form a payable total,
                  Payment Terms, Amount Due, subtotals, taxes. The document is used to request payment.
  PACKING_LIST  - primary purpose is physical shipment: Gross Weight, Net Weight, CBM, carton counts,
                  dimensions, marks & numbers. May include quantities and reference prices, but the
                  document is used by customs/logistics, NOT for payment.
  OTHER         - everything else: bills of lading, certificates of origin, phytosanitary certificates,
                  customs forms, cover pages, etc.

Word 2 — Page position:
  NEW   - first page of a new document. Has a document header with issuer, recipient, document number
          and date. Examples: "Invoice No.", "Bill To", "Shipper", "Page 1 of N", company letterhead.
  CONT  - continuation of the previous document. Contains only line items or data, no full header.

Rules:
1. Ask: is the PRIMARY PURPOSE of this page to request payment (→ INVOICE) or to describe
   what is physically inside the shipment (→ PACKING_LIST)?
2. A packing list that also shows reference unit prices is still PACKING_LIST.
3. If uncertain about type → OTHER.
4. If uncertain about position → NEW.
5. Reply with ONLY two words. No punctuation. No explanation.

--- PAGE TEXT BEGIN ---
{text}
--- PAGE TEXT END ---

Classification:"""


def _call_ollama_sync(text: str, settings: Settings) -> str:
    payload = {
        "model": settings.ollama_text_model,
        "prompt": PROMPT_TEMPLATE.format(text=text[:2000]),
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 15,
        },
    }
    resp = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json=payload,
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def _keyword_fallback(text: str) -> tuple[DocumentType, float]:
    lower = text.lower()
    inv_score = sum(1 for w in INVOICE_SIGNALS if w in lower)
    pack_score = sum(1 for w in PACKING_SIGNALS if w in lower)
    if inv_score > pack_score and inv_score >= 2:
        return DocumentType.INVOICE, 0.6
    if pack_score > inv_score and pack_score >= 2:
        return DocumentType.PACKING_LIST, 0.6
    return DocumentType.OTHER, 0.5


def _parse_response(raw: str, text: str) -> tuple[DocumentType, float, bool]:
    tokens = raw.strip().upper().split()
    type_token = tokens[0] if tokens else ""
    pos_token = tokens[1] if len(tokens) > 1 else "NEW"

    if type_token == "INVOICE":
        doc_type, confidence = DocumentType.INVOICE, 0.95
    elif type_token in ("PACKING_LIST", "PACKING"):
        doc_type, confidence = DocumentType.PACKING_LIST, 0.95
    elif type_token == "OTHER":
        doc_type, confidence = DocumentType.OTHER, 0.90
    else:
        doc_type, confidence = _keyword_fallback(text)

    is_doc_start = pos_token != "CONT"
    return doc_type, confidence, is_doc_start


def classify_page_sync(text: str, page_number: int, settings: Settings) -> tuple[DocumentType, float, str, bool]:
    """Synchronous — called from threadpool pipeline.

    Returns (DocumentType, confidence, raw_ollama_response, is_doc_start).
    Falls back to keyword scan if Ollama is unavailable or returns unexpected output.
    """
    try:
        raw = _call_ollama_sync(text, settings)
    except Exception as exc:
        raw = f"[ollama error: {exc}]"
        doc_type, confidence = _keyword_fallback(text)
        return doc_type, confidence, raw, True

    doc_type, confidence, is_doc_start = _parse_response(raw, text)
    safe_raw = raw.encode("ascii", errors="replace").decode("ascii")
    return doc_type, confidence, safe_raw[:200], is_doc_start
