import httpx
import trafilatura

from kb.adapters.text import AdaptedContent


def adapt_web(url: str) -> AdaptedContent:
    response = httpx.get(url, timeout=20)
    response.raise_for_status()
    text = trafilatura.extract(response.text) or response.text
    return AdaptedContent(
        source_type="url",
        source_uri=url,
        title=url,
        text=text,
        mime_type="text/html",
    )
