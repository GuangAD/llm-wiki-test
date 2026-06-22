import json

from typer.testing import CliRunner

from kb.cli.main import app


def test_status_reports_inventory_from_indexes_and_content_dirs(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])

    (workspace / "raw" / "20260622").mkdir(parents=True)
    (workspace / "raw" / "20260622" / "cnt_20260622_example.md").write_text(
        "raw content",
        encoding="utf-8",
    )
    (workspace / "notes" / "20260622").mkdir(parents=True)
    (workspace / "notes" / "20260622" / "note_20260622_example.md").write_text(
        "---\ntitle: Example Note\n---\nbody",
        encoding="utf-8",
    )
    (workspace / "wiki" / "topic-ai.md").write_text("# AI", encoding="utf-8")
    (workspace / "briefs" / "weekly-2026-W26.md").write_text("# Weekly", encoding="utf-8")
    (workspace / "indexes" / "recent.md").write_text(
        "# Recent\n\n- [Example Note](notes/20260622/note_20260622_example.md)\n",
        encoding="utf-8",
    )
    (workspace / "indexes" / "tags.md").write_text(
        "# Tags\n\n- ai: note_20260622_example\n- writing: note_20260622_example\n",
        encoding="utf-8",
    )
    (workspace / "indexes" / "sources.md").write_text(
        "# Sources\n\n- https://example.com/article: note_20260622_example\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["status"])
    data = json.loads(result.stdout)

    assert result.exit_code == 0
    assert data["status"] == "completed"
    assert data["counts"] == {
        "raw": 1,
        "notes": 1,
        "wiki": 1,
        "briefs": 1,
    }
    assert data["recent_notes"] == [
        {
            "title": "Example Note",
            "path": "notes/20260622/note_20260622_example.md",
        }
    ]
    assert data["tags"] == [
        {"tag": "ai", "note_ids": ["note_20260622_example"]},
        {"tag": "writing", "note_ids": ["note_20260622_example"]},
    ]
    assert data["sources"] == [
        {
            "source_uri": "https://example.com/article",
            "note_id": "note_20260622_example",
        }
    ]
    assert data["index_paths"] == [
        "indexes/recent.md",
        "indexes/tags.md",
        "indexes/sources.md",
    ]
