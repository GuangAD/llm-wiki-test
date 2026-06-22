import pytest
from pydantic import ValidationError

from kb.core.models import (
    BriefTopicsPayload,
    BriefWeeklyPayload,
    GenerationResult,
    NotePayload,
    Stance,
    TopicPayload,
)


def test_note_payload_accepts_valid_payload():
    payload = NotePayload(
        title="AI 写作工作流",
        summary="一篇关于 AI 写作工作流的摘要",
        tags=["ai", "writing", "workflow"],
        stance=Stance.APPROVE,
        key_points=["观点一", "观点二", "观点三"],
        my_judgement="值得沉淀到知识库。",
        useful_for=["选题", "写作"],
        related_topics=["ai-writing"],
    )

    assert payload.stance == Stance.APPROVE
    assert len(payload.tags) == 3


def test_note_payload_rejects_too_few_tags():
    with pytest.raises(ValidationError):
        NotePayload(
            title="AI 写作工作流",
            summary="摘要",
            tags=["ai"],
            stance=Stance.NEUTRAL,
            key_points=["观点一", "观点二", "观点三"],
            my_judgement="待观察。",
            useful_for=["选题"],
            related_topics=[],
        )


def test_generation_result_requires_completed_status():
    result = GenerationResult(
        request_id="gen_20260618143022_a8f31c92_note",
        job_id="job_20260618143022_a8f31c92",
        content_id="cnt_20260618_a8f31c92",
        generation_type="note",
        status="completed",
        created_at="2026-06-18T14:32:00+08:00",
        sources=[
            {
                "path": "raw/20260618/cnt_20260618_a8f31c92.md",
                "source_uri": "https://example.com",
            }
        ],
        payload={
            "title": "AI 写作工作流",
            "summary": "摘要",
            "tags": ["ai", "writing", "workflow"],
            "stance": "approve",
            "key_points": ["观点一", "观点二", "观点三"],
            "my_judgement": "值得沉淀。",
            "useful_for": ["选题"],
            "related_topics": [],
        },
    )

    assert result.payload.title == "AI 写作工作流"


def test_generation_result_accepts_topic_payload():
    result = GenerationResult(
        request_id="gen_20260622100000_ai-knowledge-base_topic",
        job_id="job_20260622100000_ai-knowledge-base",
        generation_type="topic",
        status="completed",
        created_at="2026-06-22T10:00:00+08:00",
        sources=[{"path": "notes/20260618/note_20260618_a.md"}],
        payload={
            "topic_key": "ai-knowledge-base",
            "title": "AI 知识库",
            "definition": "讨论个人 AI 知识库的边界和实现。",
            "conclusions": ["文件优先比一开始上向量库更稳。"],
            "disagreements": ["是否需要主题页版本记录仍未确定。"],
            "extensions": ["补充选题生成链路。"],
            "source_note_ids": ["note_20260618_a", "note_20260618_b"],
        },
    )

    assert isinstance(result.payload, TopicPayload)
    assert result.payload.topic_key == "ai-knowledge-base"


def test_generation_result_accepts_brief_topics_payload():
    result = GenerationResult(
        request_id="gen_20260622100000_brief_topics",
        job_id="job_20260622100000_brief_topics",
        generation_type="brief_topics",
        status="completed",
        created_at="2026-06-22T10:00:00+08:00",
        sources=[{"path": "indexes/recent.md"}],
        payload={
            "date": "2026-06-22",
            "topics": [
                {
                    "title": "AI 知识库为什么不该一上来做向量库",
                    "reason": "多条笔记都指向文件化和可追溯优先。",
                    "angle": "从反过度工程切入。",
                    "source_note_ids": ["note_20260618_a"],
                }
            ],
        },
    )

    assert isinstance(result.payload, BriefTopicsPayload)
    assert result.payload.topics[0].title.startswith("AI 知识库")


def test_generation_result_accepts_brief_weekly_payload():
    result = GenerationResult(
        request_id="gen_20260622100000_brief_weekly",
        job_id="job_20260622100000_brief_weekly",
        generation_type="brief_weekly",
        status="completed",
        created_at="2026-06-22T10:00:00+08:00",
        sources=[{"path": "indexes/recent.md"}],
        payload={
            "week": "2026-W26",
            "new_items": ["AI 知识库架构"],
            "key_themes": ["AI Native 知识库"],
            "open_questions": ["是否需要主题页版本记录"],
            "next_actions": ["整理 AI 知识库主题页"],
        },
    )

    assert isinstance(result.payload, BriefWeeklyPayload)
    assert result.payload.week == "2026-W26"


def test_generation_result_rejects_payload_that_does_not_match_type():
    with pytest.raises(ValidationError):
        GenerationResult(
            request_id="gen_20260622100000_wrong_topic",
            job_id="job_20260622100000_wrong",
            generation_type="topic",
            status="completed",
            created_at="2026-06-22T10:00:00+08:00",
            sources=[{"path": "notes/20260618/note_20260618_a.md"}],
            payload={
                "title": "AI 写作工作流",
                "summary": "摘要",
                "tags": ["ai", "writing", "workflow"],
                "stance": "approve",
                "key_points": ["观点一", "观点二", "观点三"],
                "my_judgement": "值得沉淀。",
                "useful_for": ["选题"],
                "related_topics": [],
            },
        )
