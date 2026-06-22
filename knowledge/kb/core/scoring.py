import re


def _query_terms(query: str) -> list[str]:
    return [term.lower() for term in re.split(r"\s+", query.strip()) if term]


def _contains_any(query_terms: list[str], value: str) -> bool:
    lower = value.lower()
    return any(term in lower for term in query_terms)


def score_note(query: str, note: dict) -> int:
    terms = _query_terms(query)
    score = 0
    if _contains_any(terms, note.get("title", "")):
        score += 5
    if any(_contains_any(terms, tag) for tag in note.get("tags", [])):
        score += 4
    if _contains_any(terms, note.get("summary", "")):
        score += 3
    if _contains_any(terms, note.get("body", "")):
        score += 2
    if _contains_any(terms, note.get("source_uri", "")):
        score += 1
    return score
