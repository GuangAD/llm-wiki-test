from pathlib import Path

import yaml
from pydantic import BaseModel


class PathsConfig(BaseModel):
    raw: str
    notes: str
    indexes: str
    prompts: str
    state: str
    logs: str


class IngestConfig(BaseModel):
    allowed_inputs: list[str]
    lock_enabled: bool


class AskConfig(BaseModel):
    max_notes: int
    min_score: int


class Config(BaseModel):
    paths: PathsConfig
    phase: int
    ingest: IngestConfig
    ask: AskConfig


def load_config(root: Path) -> Config:
    data = yaml.safe_load((root / "kb.yaml").read_text(encoding="utf-8"))
    return Config.model_validate(data)
