from kb.core.scoring import score_note


def test_score_note_weights_fields():
    note = {
        "title": "AI 写作",
        "tags": ["ai", "writing"],
        "summary": "知识管理摘要",
        "body": "正文摘要提到工作流",
        "source_uri": "https://example.com",
    }

    assert score_note("AI writing 工作流", note) == 11
