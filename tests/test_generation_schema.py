import pytest
from pydantic import ValidationError

from kb.core.models import GenerationResult, NotePayload, Stance


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
