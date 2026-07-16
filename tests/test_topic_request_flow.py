import json

import frontmatter
from typer.testing import CliRunner

from kb.cli.main import app
from kb.services.ingest_service import _write_topic_requests


def test_topic_requests_use_topic_scoped_paths(workspace):
    note_dir = workspace / "notes" / "20260622"
    note_dir.mkdir(parents=True)
    for number in range(2):
        path = note_dir / f"note_{number}.md"
        path.write_text(
            frontmatter.dumps(
                frontmatter.Post(
                    "body",
                    id=f"note_{number}",
                    title=f"Note {number}",
                    topic_keys=["ai", "writing"],
                )
            ),
            encoding="utf-8",
        )

    paths = _write_topic_requests(workspace, "job_20260622120000_example", ["ai", "writing"])

    assert [path.name for path in paths] == [
        "job_20260622120000_example-topic-ai.md",
        "job_20260622120000_example-topic-writing.md",
    ]


def test_manual_compile_request_includes_existing_topic(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    note_dir = workspace / "notes" / "20260622"
    note_dir.mkdir(parents=True)
    for number in range(2):
        (note_dir / f"note_{number}.md").write_text(
            frontmatter.dumps(
                frontmatter.Post(
                    "body",
                    id=f"note_{number}",
                    title=f"Note {number}",
                    topic_keys=["ai"],
                )
            ),
            encoding="utf-8",
        )
    topic_path = workspace / "wiki" / "topic-ai.md"
    topic_path.write_text(
        frontmatter.dumps(
            frontmatter.Post(
                "old topic",
                topic_key="ai",
                title="AI",
                source_note_ids=["note_0", "note_1"],
            )
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["compile", "--topic-key", "ai"])
    data = json.loads(result.stdout)
    request = frontmatter.loads(
        (workspace / data["generation_request_path"]).read_text(encoding="utf-8")
    )

    assert data["status"] == "needs_generation"
    assert request.metadata["source_paths"] == [
        "notes/20260622/note_0.md",
        "notes/20260622/note_1.md",
        "wiki/topic-ai.md",
    ]
