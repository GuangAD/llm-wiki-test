from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Stance(StrEnum):
    APPROVE = "approve"
    DOUBT = "doubt"
    NEUTRAL = "neutral"
    TO_DO = "todo"


class NotePayload(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    tags: list[str] = Field(min_length=3, max_length=5)
    stance: Stance
    key_points: list[str] = Field(min_length=3, max_length=7)
    my_judgement: str = Field(min_length=1)
    useful_for: list[str]
    related_topics: list[str]


class GenerationSource(BaseModel):
    path: str
    source_uri: str | None = None


class GenerationResult(BaseModel):
    request_id: str
    job_id: str
    content_id: str
    generation_type: Literal["note"]
    status: Literal["completed"]
    created_at: str
    sources: list[GenerationSource]
    payload: NotePayload


class CliResponse(BaseModel):
    ok: bool
    command: str
    status: str
    message: str | None = None
    next_action: str | None = None
