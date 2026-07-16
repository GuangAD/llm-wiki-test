from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


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


class TopicPayload(BaseModel):
    topic_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    conclusions: list[str]
    disagreements: list[str]
    extensions: list[str]
    source_note_ids: list[str] = Field(min_length=2)


class BriefTopicItem(BaseModel):
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    source_note_ids: list[str]


class BriefTopicsPayload(BaseModel):
    date: str = Field(min_length=1)
    topics: list[BriefTopicItem] = Field(min_length=1)


class BriefWeeklyPayload(BaseModel):
    week: str = Field(min_length=1)
    new_items: list[str]
    key_themes: list[str]
    open_questions: list[str]
    next_actions: list[str]


class AnswerCitation(BaseModel):
    path: str = Field(min_length=1)
    source_uri: str | None = None


class AnswerPayload(BaseModel):
    title: str = Field(min_length=1)
    question: str = Field(min_length=1)
    answer_markdown: str = Field(min_length=1)
    citations: list[AnswerCitation] = Field(min_length=1)
    topic_keys: list[str]


class LintIssue(BaseModel):
    code: str = Field(min_length=1)
    severity: Literal["error", "warning", "info"]
    target_paths: list[str]
    description: str = Field(min_length=1)
    suggested_action: str = Field(min_length=1)
    topic_key: str | None = None


class LintPayload(BaseModel):
    summary: str = Field(min_length=1)
    issues: list[LintIssue]


class GenerationSource(BaseModel):
    path: str
    source_uri: str | None = None


class GenerationResult(BaseModel):
    request_id: str
    job_id: str
    content_id: str | None = None
    generation_type: Literal[
        "note",
        "topic",
        "answer",
        "lint",
        "brief_topics",
        "brief_weekly",
    ]
    status: Literal["completed"]
    created_at: str
    sources: list[GenerationSource]
    payload: (
        NotePayload
        | TopicPayload
        | AnswerPayload
        | LintPayload
        | BriefTopicsPayload
        | BriefWeeklyPayload
    )

    @model_validator(mode="after")
    def validate_payload_matches_generation_type(self) -> "GenerationResult":
        expected = {
            "note": NotePayload,
            "topic": TopicPayload,
            "answer": AnswerPayload,
            "lint": LintPayload,
            "brief_topics": BriefTopicsPayload,
            "brief_weekly": BriefWeeklyPayload,
        }[self.generation_type]
        if not isinstance(self.payload, expected):
            raise ValueError("payload does not match generation_type")
        return self


class CliResponse(BaseModel):
    ok: bool
    command: str
    status: str
    message: str | None = None
    next_action: str | None = None
