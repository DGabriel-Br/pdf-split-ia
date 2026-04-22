import httpx
from app.config import Settings
from app.models import DocumentType

# ── Title-based signals (checked against first line of extracted text) ──────
# Most reliable: the document title is almost always on the first line.
_TITLE_PACKING = [
    "packing list",     # "Packing List", "PACKING LIST"
    "p a c k i n g",   # "P A C K I N G L I S T" (Indian spaced-letter format)
    "delivery note",    # Robert Bosch and similar suppliers
    "lieferschein",     # German: delivery note (Robert Bosch German docs)
]
_TITLE_INVOICE = [
    "export invoice",   # "EXPORT INVOICE" (Reify, Indian format)
    "e x p o r t i",   # "E X P O R T I N V O I C E" (Prem, Indian spaced-letter format)
]
_TITLE_OTHER = [
    "export value declaration",
    "annexure",
    "certificate of origin",
    "bill of lading",
    "shipping bill",
    "phytosanitary",
    "contract",                  # Standalone trade contract (Chinese supplier)
    "transport order",           # Robert Bosch transport/shipping orders
    "ausfuhrbegleitdokument",    # German: export accompanying document (EU customs)
    "betriebskontinuit",         # German: business continuity export doc
    "europäische union",         # EU customs documents header
    "europaische union",         # ASCII variant (without umlaut)
]

# ── Keyword signals for score-based pre-filter (fallback after title check) ──
_INVOICE_SIGNALS = [
    "payment terms",    # Very common in invoice headers
    "amount due",
    "unit price",
    "subtotal",
    "payable to",
    "remittance",
    "bank transfer",
    "wire transfer",
    "swift code",       # Bank payment details (Chinese supplier invoices)
    "beneficiary:",     # Bank payment details (Chinese supplier invoices)
    "currency:",        # Explicit currency field (Chinese supplier)
]
_PACKING_SIGNALS = [
    "packing list",
    "gross weight",
    "net weight",
    "cbm",
    "marks & numbers",
    "marks and numbers",
    "n.w.",
    "g.w.",
    "packing id",       # Indian supplier specific (Prem Industries, Reify)
    "cartons",
    "no. of cartons",
]

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
                  of origin, phytosanitary certificates, customs forms, cover pages, bank documents,
                  trade contracts, annexures, etc.

Word 2 — Page position:
  NEW   - first page of a new document. Has a document header with issuer, recipient, document number
          and date. Examples: "Invoice No.", "Bill To", "Shipper", "Page 1 of N", company letterhead.
  CONT  - continuation of the previous document. Contains only line items or data, no full header.

Rules:
1. The DOCUMENT TITLE (first prominent line) is the most reliable signal:
   - "EXPORT INVOICE", "Invoice", "E X P O R T  I N V O I C E" → INVOICE
   - "PACKING LIST", "Packing List", "P A C K I N G  L I S T" → PACKING_LIST
   - "CONTRACT", "ANNEXURE", "EXPORT VALUE DECLARATION" → OTHER
2. Two documents from the SAME supplier with IDENTICAL headers (exporter, buyer, invoice ref)
   can be different types — use the document TITLE to distinguish them.
3. A packing list that also shows reference unit prices is still PACKING_LIST.
4. IMPORTANT: a form or declaration with blank fields labelled "Invoice No." or "Shipping Bill No."
   is NOT an invoice — it is a customs/export form → OTHER.
5. A standalone "CONTRACT" between seller and buyer → OTHER (not INVOICE).
6. If uncertain about type → OTHER. If uncertain about position → NEW.
7. Reply with ONLY two words. No punctuation. No explanation.

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
    """Title-first pre-filter, then keyword scoring. Returns (type, confidence, is_doc_start) or None."""
    stripped = text.strip()
    first_line = stripped.split("\n")[0].strip().lower()
    lower = stripped.lower()
    header = lower[:500]

    # 1. First-line title match — "Invoice" alone or "Invoice N/M" / "Invoice 1 of 3" format
    if first_line == "invoice" or first_line.startswith("invoice "):
        return DocumentType.INVOICE, 0.93, True
    if first_line in ("packing list", "packing  list"):
        return DocumentType.PACKING_LIST, 0.93, True

    # 2. Title keywords anywhere in first 250 chars
    other_title = any(t in header for t in _TITLE_OTHER)
    packing_title = any(t in header for t in _TITLE_PACKING)
    invoice_title = any(t in header for t in _TITLE_INVOICE)

    if other_title and not invoice_title and not packing_title:
        return DocumentType.OTHER, 0.92, True
    if packing_title and not invoice_title:
        return DocumentType.PACKING_LIST, 0.92, True
    if invoice_title and not packing_title:
        return DocumentType.INVOICE, 0.92, True

    # 3. Keyword score fallback
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
    Pre-filter skips Ollama for pages with unambiguous title or keyword signal.
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
