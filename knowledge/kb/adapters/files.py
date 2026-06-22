from pathlib import Path

import fitz

from kb.adapters.text import AdaptedContent


def _read_pdf(path: Path) -> str:
    with fitz.open(path) as document:
        return "\n".join(page.get_text() for page in document)


def adapt_file(path: Path) -> AdaptedContent:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _read_pdf(path)
        mime_type = "application/pdf"
    else:
        text = path.read_text(encoding="utf-8")
        mime_type = "text/markdown" if suffix == ".md" else "text/plain"
    return AdaptedContent(
        source_type=suffix.lstrip(".") or "file",
        source_uri=str(path.resolve()),
        title=path.stem,
        text=text,
        mime_type=mime_type,
    )
