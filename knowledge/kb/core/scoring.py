import re


def _query_terms(query: str) -> list[str]:
    terms = [term.lower() for term in re.findall(r"[a-zA-Z0-9_-]+", query)]
    for segment in re.findall(r"[\u4e00-\u9fff]+", query):
        terms.append(segment)
        terms.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return list(dict.fromkeys(term for term in terms if term))


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


def score_wiki(query: str, page: dict) -> int:
    terms = _query_terms(query)
    score = 0
    if _contains_any(terms, page.get("title", "")):
        score += 8
    if _contains_any(terms, page.get("topic_key", "")):
        score += 6
    if _contains_any(terms, page.get("body", "")):
        score += 4
    return score
