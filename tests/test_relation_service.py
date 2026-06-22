import frontmatter

from kb.services.relation_service import sync_relations
from kb.storage.note_store import write_note


def _read_note(path):
    return frontmatter.loads(path.read_text(encoding="utf-8"))


def test_sync_relations_writes_bidirectional_related_note_ids(workspace):
    first_path = write_note(
        workspace,
        "20260618",
        "note_20260618_a",
        {
            "id": "note_20260618_a",
            "title": "AI knowledge base architecture",
            "tags": ["ai", "knowledge", "workflow"],
            "summary": "File based knowledge base.",
            "related_note_ids": [],
            "topic_keys": ["ai-knowledge-base"],
        },
        "## 摘要\n\n第一条",
    )
    second_path = write_note(
        workspace,
        "20260618",
        "note_20260618_b",
        {
            "id": "note_20260618_b",
            "title": "AI knowledge base workflow",
            "tags": ["ai", "knowledge", "writing"],
            "summary": "Writing workflow.",
            "related_note_ids": [],
            "topic_keys": [],
        },
        "## 摘要\n\n第二条",
    )

    result = sync_relations(workspace, "note_20260618_b", ["AI Knowledge Base"])

    first = _read_note(first_path)
    second = _read_note(second_path)
    assert first.metadata["related_note_ids"] == ["note_20260618_b"]
    assert second.metadata["related_note_ids"] == ["note_20260618_a"]
    assert second.metadata["topic_keys"] == ["ai-knowledge-base"]
    assert result["related_note_ids"] == ["note_20260618_a"]
    assert result["compilable_topic_keys"] == ["ai-knowledge-base"]


def test_sync_relations_does_not_link_low_score_notes(workspace):
    write_note(
        workspace,
        "20260618",
        "note_20260618_a",
        {
            "id": "note_20260618_a",
            "title": "Python testing",
            "tags": ["python", "testing", "pytest"],
            "summary": "Testing notes.",
            "related_note_ids": [],
            "topic_keys": [],
        },
        "## 摘要\n\n第一条",
    )
    current_path = write_note(
        workspace,
        "20260618",
        "note_20260618_b",
        {
            "id": "note_20260618_b",
            "title": "AI writing workflow",
            "tags": ["ai", "writing", "workflow"],
            "summary": "Writing notes.",
            "related_note_ids": [],
            "topic_keys": [],
        },
        "## 摘要\n\n第二条",
    )

    result = sync_relations(workspace, "note_20260618_b", ["AI Writing"])

    current = _read_note(current_path)
    assert current.metadata["related_note_ids"] == []
    assert current.metadata["topic_keys"] == ["ai-writing"]
    assert result["related_note_ids"] == []
    assert result["compilable_topic_keys"] == []


def test_sync_relations_keeps_topic_keys_stable(workspace):
    write_note(
        workspace,
        "20260618",
        "note_20260618_a",
        {
            "id": "note_20260618_a",
            "title": "AI knowledge base",
            "tags": ["ai", "knowledge", "workflow"],
            "summary": "Knowledge base notes.",
            "related_note_ids": [],
            "topic_keys": [],
        },
        "## 摘要\n\n第一条",
    )

    result = sync_relations(workspace, "note_20260618_a", [" AI Knowledge Base! "])

    assert result["topic_keys"] == ["ai-knowledge-base"]
