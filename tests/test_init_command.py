import json

from typer.testing import CliRunner

from kb.cli.main import app


def test_init_creates_directories(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    result = CliRunner().invoke(app, ["init"])
    data = json.loads(result.stdout)

    assert result.exit_code == 0
    assert data["status"] == "completed"
    for path in [
        "raw",
        "notes",
        "wiki",
        "briefs",
        "indexes",
        "prompts",
        "state/jobs",
        "state/generation_requests",
        "state/generation_results",
        "state/locks",
        "logs",
    ]:
        assert (workspace / path).exists()
    assert (workspace / "prompts" / "note.md").exists()
    assert (workspace / "prompts" / "topic.md").exists()
    assert (workspace / "prompts" / "brief-topics.md").exists()
    assert (workspace / "prompts" / "brief-weekly.md").exists()


def test_init_does_not_overwrite_existing_prompt(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    prompt_path = workspace / "prompts" / "note.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("custom prompt", encoding="utf-8")

    result = CliRunner().invoke(app, ["init"])

    assert result.exit_code == 0
    assert prompt_path.read_text(encoding="utf-8") == "custom prompt"


def test_init_does_not_overwrite_existing_brief_prompt(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    prompt_path = workspace / "prompts" / "brief-weekly.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("custom weekly prompt", encoding="utf-8")

    result = CliRunner().invoke(app, ["init"])

    assert result.exit_code == 0
    assert prompt_path.read_text(encoding="utf-8") == "custom weekly prompt"
