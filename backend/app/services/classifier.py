import httpx
from app.config import Settings
from app.models import DocumentType

# Keyword signals for pre-filter — only highly specific multi-word terms
# to avoid false positives from generic words like "total", "amount", "rate"
_INVOICE_SIGNALS = [
    "payment terms", "amount due", "unit price", "subtotal",
    "payable to", "remittance", "bank transfer", "wire transfer",
]
_PACKING_SIGNALS = [
    "packing list", "gross weight", "net weight", "cbm",
    "marks & numbers", "marks and numbers", "n.w.", "g.w.",
]

# Minimum score AND dominance ratio required to skip Ollama
_PREFILTER_MIN_SCORE = 3
_PREFILTER_DOMINANCE = 2

PROMPT_TEMPLATE = """\
You are a document classification engine for import trade documents.
Analyze the page text and reply with EXACTLY TWO words separated by a space.

Word 1 — Document type:
  INVOICE       - primary purpose is financial settlement: a filled table of goods with unit prices
                  that add up to a payable total, Payment Terms, Amount Due, subtotals, taxes.
                  The document is used to REQUEST PAYMENT from the buyer.
  PACKING_LIST  - primary purpose is physical shipment: Gross Weight, Net Weight, CBM, carton counts,
                  dimensions, marks & numbers. May include quantities and reference prices, but the
                  document is used by customs/logistics, NOT for payment.
  OTHER         - everything else: bills of lading, export declarations, shipping bills, certificates
                  of origin, phytosanitary certificates, customs forms, cover pages, bank documents, etc.

Word 2 — Page position:
  NEW   - first page of a new document. Has a document header with issuer, recipient, document number
          and date. Examples: "Invoice No.", "Bill To", "Shipper", "Page 1 of N", company letterhead.
  CONT  - continuation of the previous document. Contains only line items or data, no full header.

Rules:
1. Ask: is the PRIMARY PURPOSE of this page to request payment (→ INVOICE) or to describe
   what is physically inside the shipment (→ PACKING_LIST)?
2. A packing list that also shows reference unit prices is still PACKING_LIST.
3. IMPORTANT: a form or declaration that has blank fields labelled "Invoice No." or "Shipping Bill No."
   is NOT an invoice — it is a customs/export form → OTHER.
4. If uncertain about type → OTHER.
5. If uncertain about position → NEW.
6. Reply with ONLY two words. No punctuation. No explanation.

--- PAGE TEXT BEGIN ---
{text}
--- PAGE TEXT END ---

Classification:"""


def _keyword_scores(text: str) -> tuple[int, int]:
    lower = text.lower()
    inv = sum(1 for w in _INVOICE_SIGNALS if w in lower)
    pack = sum(1 for w in _PACKING_SIGNALS if w in lower)
    return inv, pack


def _prefilter(text: str) -> tuple[DocumentType, float, bool] | None:
    """Return (doc_type, confidence, is_doc_start=True) if signal is unambiguous, else None."""
    inv, pack = _keyword_scores(text)
    if inv >= _PREFILTER_MIN_SCORE and inv >= pack * _PREFILTER_DOMINANCE:
        return DocumentType.INVOICE, 0.85, True
    if pack >= _PREFILTER_MIN_SCORE and pack >= inv * _PREFILTER_DOMINANCE:
        return DocumentType.PACKING_LIST, 0.85, True
    return None


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
    inv, pack = _keyword_scores(text)
    if inv > pack and inv >= 2:
        return DocumentType.INVOICE, 0.6
    if pack > inv and pack >= 2:
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

    Returns (DocumentType, confidence, raw_label, is_doc_start).
    Pre-filter skips Ollama for pages with unambiguous keyword signal.
    Falls back to keyword scan if Ollama is unavailable or returns unexpected output.
    """
    prefilter = _prefilter(text)
    if prefilter is not None:
        doc_type, confidence, is_doc_start = prefilter
        return doc_type, confidence, f"[pre-filter: {doc_type.value}]", is_doc_start

    try:
        raw = _call_ollama_sync(text, settings)
    except Exception as exc:
        raw = f"[ollama error: {exc}]"
        doc_type, confidence = _keyword_fallback(text)
        return doc_type, confidence, raw, True

    doc_type, confidence, is_doc_start = _parse_response(raw, text)
    safe_raw = raw.encode("ascii", errors="replace").decode("ascii")
    return doc_type, confidence, safe_raw[:200], is_doc_start
