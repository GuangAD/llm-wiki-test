from kb.core.scoring import score_note, score_wiki


def test_score_note_weights_fields():
    note = {
        "title": "AI 写作",
        "tags": ["ai", "writing"],
        "summary": "知识管理摘要",
        "body": "正文摘要提到工作流",
        "source_uri": "https://example.com",
    }

    assert score_note("AI writing 工作流", note) == 11


def test_score_wiki_matches_chinese_bigrams():
    page = {
        "title": "个人知识管理",
        "topic_key": "personal-knowledge-management",
        "body": "知识库会持续积累并更新结论。",
    }

    assert score_wiki("为什么知识库能够积累知识", page) > 0
