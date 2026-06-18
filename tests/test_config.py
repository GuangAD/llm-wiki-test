from pathlib import Path

from kb.config.loader import load_config


def test_load_config_reads_minimum_fields(workspace: Path):
    (workspace / "kb.yaml").write_text(
        """
paths:
  raw: raw
  notes: notes
  indexes: indexes
  prompts: prompts
  state: state
  logs: logs
phase: 1
ingest:
  allowed_inputs: [url, txt, md, pdf, text]
  lock_enabled: true
ask:
  max_notes: 5
  min_score: 1
""".strip(),
        encoding="utf-8",
    )

    config = load_config(workspace)

    assert config.phase == 1
    assert config.paths.raw == "raw"
    assert config.ingest.lock_enabled is True
    assert config.ask.max_notes == 5
