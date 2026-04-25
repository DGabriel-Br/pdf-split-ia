import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

import anthropic
from app.config import get_settings
from app.services.correction_store import load_unreviewed, save_last_review_time

log = logging.getLogger(__name__)

# Current hardcoded lists — sent to Claude so it knows what already exists
_CURRENT_LISTS = {
    "_TITLE_OTHER": [
        "export value declaration", "annexure", "certificate of origin",
        "bill of lading", "shipping bill", "phytosanitary", "contract",
        "transport order", "ausfuhrbegleitdokument", "betriebskontinuit",
        "europäische union", "europaische union",
    ],
    "_TITLE_PACKING": [
        "packing list", "p a c k i n g", "delivery note", "lieferschein",
    ],
    "_TITLE_INVOICE": [
        "export invoice", "e x p o r t i",
    ],
    "_INVOICE_SIGNALS": [
        "payment terms", "amount due", "unit price", "subtotal", "payable to",
        "remittance", "bank transfer", "wire transfer", "swift code",
        "beneficiary:", "currency:",
    ],
    "_PACKING_SIGNALS": [
        "packing list", "gross weight", "net weight", "cbm", "marks & numbers",
        "marks and numbers", "n.w.", "g.w.", "packing id", "cartons",
        "no. of cartons",
    ],
}

_REVIEW_PROMPT = """\
You are improving the pre-filter of a document classifier for import trade documents.

The pre-filter checks page text against keyword lists to classify documents without calling an AI model.
Here are the current lists:

_TITLE_OTHER (page classified as OTHER if first 500 chars contain any of these):
{title_other}

_TITLE_PACKING (classified as PACKING_LIST):
{title_packing}

_TITLE_INVOICE (classified as INVOICE):
{title_invoice}

_INVOICE_SIGNALS (keyword score signals for INVOICE):
{inv_signals}

_PACKING_SIGNALS (keyword score signals for PACKING_LIST):
{pack_signals}

The following pages were MISCLASSIFIED by the current system. \
For each, the first ~300 chars of OCR text are shown, along with the original (wrong) type and the corrected (right) type:

{corrections}

Analyze each misclassified page and determine what specific phrase from its text should be added \
to which list to prevent this misclassification in the future.

Respond with ONLY valid JSON — no explanation, no markdown:
{{
  "_TITLE_OTHER": [],
  "_TITLE_PACKING": [],
  "_TITLE_INVOICE": [],
  "_INVOICE_SIGNALS": [],
  "_PACKING_SIGNALS": []
}}

Rules:
- Only add phrases that actually appear in the page text shown above
- Add to the list that corresponds to the CORRECTED type (e.g. OTHER → INVOICE means add to an INVOICE list)
- Lowercase, 2-6 words per phrase
- Do NOT add phrases already present in the current lists above
- Return empty arrays for lists that need no additions
- Be conservative: only add if the phrase is a strong, distinctive signal"""


def _format_corrections(records: list[dict]) -> str:
    lines = []
    for i, r in enumerate(records, 1):
        lines.append(
            f"[{i}] {r['original_type']} → {r['corrected_type']}\n"
            f"    Text: {r.get('text_preview', '(no text)')[:280]}"
        )
    return "\n\n".join(lines)


def _call_claude(prompt: str) -> dict:
    s = get_settings()
    if not s.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured.")

    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    message = client.messages.create(
        model=s.reviewer_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(raw[start:end])
    raise ValueError(f"Resposta inesperada do Claude: {raw[:200]}")


def _load_learned() -> dict:
    path = get_settings().learned_patterns_file
    if not os.path.isfile(path):
        return {k: [] for k in _CURRENT_LISTS}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _merge_and_save(additions: dict) -> dict:
    """Merge new additions into learned_patterns.json (no duplicates)."""
    learned = _load_learned()
    all_existing = {item for lst in _CURRENT_LISTS.values() for item in lst}

    for key, new_items in additions.items():
        if key not in learned:
            learned[key] = []
        existing = set(learned[key]) | all_existing
        for item in new_items:
            if isinstance(item, str) and item.strip() and item.lower() not in existing:
                learned[key].append(item.lower().strip())
                existing.add(item.lower().strip())

    path = get_settings().learned_patterns_file
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(learned, f, ensure_ascii=False, indent=2)
    return learned


def analyze_and_propose() -> str | None:
    """
    Analyze unreviewed corrections using Claude API, update learned_patterns.json,
    and save a proposal log. Returns the proposal file path or None if nothing to do.
    """
    records = load_unreviewed()
    if not records:
        log.info("Revisao semanal: nenhuma correcao nova.")
        return None

    log.info("Revisao semanal: analisando %d correcao(oes) com Claude API.", len(records))

    prompt = _REVIEW_PROMPT.format(
        title_other=_CURRENT_LISTS["_TITLE_OTHER"],
        title_packing=_CURRENT_LISTS["_TITLE_PACKING"],
        title_invoice=_CURRENT_LISTS["_TITLE_INVOICE"],
        inv_signals=_CURRENT_LISTS["_INVOICE_SIGNALS"],
        pack_signals=_CURRENT_LISTS["_PACKING_SIGNALS"],
        corrections=_format_corrections(records),
    )

    try:
        additions = _call_claude(prompt)
    except Exception as exc:
        log.error("Falha na chamada Claude API durante revisao: %s", exc)
        return None

    learned = _merge_and_save(additions)
    log.info("learned_patterns.json atualizado: %s", {k: v for k, v in learned.items() if v})

    now = datetime.now(timezone.utc)
    s = get_settings()
    out_dir = os.path.dirname(os.path.abspath(s.corrections_file))
    path = os.path.join(out_dir, f"classifier_proposal_{now.strftime('%Y%m%d')}.json")

    report = {
        "generated_at": now.isoformat(),
        "corrections_analyzed": len(records),
        "additions_applied": {k: v for k, v in additions.items() if v},
        "learned_patterns_current": learned,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    save_last_review_time(now.isoformat())
    log.info("Revisao semanal concluida. Log: %s", path)
    return path
