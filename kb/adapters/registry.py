from pathlib import Path

from kb.adapters.files import adapt_file
from kb.adapters.text import AdaptedContent, adapt_text
from kb.adapters.web import adapt_web


def adapt_input(value: str) -> AdaptedContent:
    if value.startswith(("http://", "https://")):
        return adapt_web(value)
    path = Path(value)
    if path.exists():
        return adapt_file(path)
    return adapt_text(value)
