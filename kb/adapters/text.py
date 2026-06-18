from pydantic import BaseModel, Field


class AdaptedContent(BaseModel):
    source_type: str
    source_uri: str
    title: str
    text: str = Field(min_length=1)
    mime_type: str


def adapt_text(value: str) -> AdaptedContent:
    return AdaptedContent(
        source_type="text",
        source_uri=f"text:{value[:64]}",
        title=value[:80] or "Untitled text",
        text=value,
        mime_type="text/plain",
    )
