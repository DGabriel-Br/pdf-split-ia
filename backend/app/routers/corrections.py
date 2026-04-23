from collections import Counter, defaultdict
from fastapi import APIRouter
from app.services.correction_store import load_all

router = APIRouter()

_STOPWORDS = {
    "the", "and", "for", "this", "that", "with", "from", "have", "been",
    "will", "are", "was", "has", "not", "but", "its", "page", "date",
    "name", "ref", "no", "to", "of", "in", "a", "an",
}


def _first_line(text: str) -> str:
    return text.strip().split("\n")[0][:120] if text else ""


def _keyword_candidates(texts: list[str], n: int = 12) -> list[str]:
    """Return most frequent non-trivial words across text excerpts."""
    words: list[str] = []
    for t in texts:
        for w in t.lower().split():
            w = w.strip(".,;:()-/\\\"'")
            if len(w) > 4 and w not in _STOPWORDS and w.replace(".", "").isalpha():
                words.append(w)
    return [w for w, _ in Counter(words).most_common(n)]


@router.get("/corrections/report")
async def corrections_report() -> dict:
    """
    Returns a grouped summary of user corrections for review.
    Use this to identify patterns and improve the classifier pre-filter.
    """
    records = load_all()
    if not records:
        return {"total": 0, "transitions": {}}

    by_transition: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        key = f"{r['original_type']} → {r['corrected_type']}"
        by_transition[key].append(r)

    transitions = {}
    for transition, items in sorted(by_transition.items(), key=lambda x: -len(x[1])):
        texts = [r.get("text_preview", "") for r in items]
        transitions[transition] = {
            "count": len(items),
            "first_lines": list({_first_line(t) for t in texts if t})[:20],
            "keyword_candidates": _keyword_candidates(texts),
            "examples": [
                {
                    "date": r["timestamp"][:10],
                    "job_id": r["job_id"][:8],
                    "page": r["page_number"],
                    "pdf_page": r.get("pdf_page"),
                    "text_preview": r.get("text_preview", "")[:250],
                }
                for r in items[:5]
            ],
        }

    return {"total": len(records), "transitions": transitions}
