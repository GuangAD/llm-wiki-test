# AI Knowledge Base Phase 1 Implementation Plan

> 归档说明：本文是 Phase 1 的历史实施计划。文中的 `kb/`、`raw/`、`notes/`、`indexes/`、`prompts/`、`state/` 等路径按当时“仓库根目录即知识库根目录”的结构描述；当前结构已调整为功能代码位于 `knowledge/kb/`，知识库运行目录位于 `knowledge/` 下。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 AI 知识库 Phase 1：本地 CLI 能完成 `init -> ingest -> generation_request -> generation_result 校验 -> note 落盘 -> Markdown indexes -> ask` 的最小闭环。

**Architecture:** `kb` 是唯一执行内核，智能体只通过自然语言或快捷入口调用 `kb` 命令。Phase 1 不接 LLM API，不做 topic 编译，不做 brief；`kb` 负责文件读写、状态、schema 校验和索引，智能体负责根据 `GenerationRequest` 生成 `GenerationResult`。

**Tech Stack:** Python 3.12, uv, Typer, Pydantic, pytest, ruff, python-frontmatter, PyYAML, httpx, trafilatura, PyMuPDF.

---

## Scope

Phase 1 只实现：

- `kb init`
- `kb ingest <input>`
- `kb ingest --continue <job_id>`
- `kb ask <question>`
- 文件存储、job state、generation request/result、note、Markdown indexes
- JSON stdout 返回协议

Phase 1 不实现：

- Claude/OpenAI/本地模型 API
- topic compiler
- `indexes/topics.md`
- brief topics / brief weekly
- GitHub 专用 adapter
- 微信公众号专用 adapter
- 向量库、数据库、Web 前端

## File Structure

创建以下文件：

```text
pyproject.toml
kb.yaml
kb/
  __init__.py
  cli/
    __init__.py
    main.py
    commands/
      __init__.py
      init.py
      ingest.py
      ask.py
  core/
    __init__.py
    ids.py
    errors.py
    atomic.py
    locks.py
    scoring.py
    models.py
  config/
    __init__.py
    loader.py
  storage/
    __init__.py
    paths.py
    raw_store.py
    note_store.py
    job_store.py
    generation_store.py
    index_store.py
  adapters/
    __init__.py
    registry.py
    web.py
    files.py
    text.py
  services/
    __init__.py
    ingest_service.py
    ask_service.py
  prompts/
    note.md
tests/
  conftest.py
  test_ids.py
  test_atomic.py
  test_config.py
  test_init_command.py
  test_generation_schema.py
  test_ingest_flow.py
  test_ask_scoring.py
```

运行时由 `kb init` 创建：

```text
raw/
notes/
indexes/
prompts/
state/jobs/
state/generation_requests/
state/generation_results/
state/locks/
logs/
```

## Shared Rules

- 所有 CLI 命令默认 stdout 输出 JSON。
- 所有写文件操作必须 `*.tmp -> rename` 原子替换。
- 同一时间只允许一个 `kb ingest`，锁文件为 `state/locks/ingest.lock`。
- `GenerationRequest` 是 Markdown + YAML frontmatter。
- `GenerationResult` 是 YAML。
- 智能体只能写 `result_path`，不能直接写 `notes/`、`indexes/`、`wiki/`。
- Phase 1 `ask` 扫描 `notes/**/*.md`，按关键词打分，不读 topic。

---

### Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `kb/__init__.py`
- Create: `kb/cli/__init__.py`
- Create: `kb/cli/main.py`
- Create: `kb/cli/commands/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "fuxi-kb"
version = "0.1.0"
description = "Local AI knowledge base CLI"
requires-python = ">=3.12"
dependencies = [
  "typer>=0.12.0",
  "pydantic>=2.7.0",
  "python-frontmatter>=1.1.0",
  "pyyaml>=6.0.0",
  "httpx>=0.27.0",
  "trafilatura>=1.9.0",
  "pymupdf>=1.24.0"
]

[project.scripts]
kb = "kb.cli.main:app"

[dependency-groups]
dev = [
  "pytest>=8.0.0",
  "ruff>=0.5.0"
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package files**

Create empty `__init__.py` files in:

```text
kb/__init__.py
kb/cli/__init__.py
kb/cli/commands/__init__.py
```

- [ ] **Step 3: Create CLI entry**

```python
# kb/cli/main.py
import typer

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Local AI knowledge base CLI."""
```

- [ ] **Step 4: Create pytest fixture**

```python
# tests/conftest.py
from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path
```

- [ ] **Step 5: Run baseline checks**

Run:

```bash
uv run pytest
uv run ruff check .
```

Expected:

```text
no tests ran
All checks passed!
```

If the project is not yet managed by `uv`, run:

```bash
uv sync
```

Expected: dependencies install successfully.

---

### Task 2: Core Models And Schemas

**Files:**
- Create: `kb/core/models.py`
- Create: `tests/test_generation_schema.py`

- [ ] **Step 1: Write schema tests**

```python
# tests/test_generation_schema.py
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
        sources=[{"path": "raw/20260618/cnt_20260618_a8f31c92.md", "source_uri": "https://example.com"}],
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_generation_schema.py -v
```

Expected: FAIL because `kb.core.models` does not exist.

- [ ] **Step 3: Implement models**

```python
# kb/core/models.py
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Stance(StrEnum):
    APPROVE = "approve"
    DOUBT = "doubt"
    NEUTRAL = "neutral"
    TO_DO = "todo"


class NotePayload(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    tags: list[str] = Field(min_length=3, max_length=5)
    stance: Stance
    key_points: list[str] = Field(min_length=3, max_length=7)
    my_judgement: str = Field(min_length=1)
    useful_for: list[str]
    related_topics: list[str]


class GenerationSource(BaseModel):
    path: str
    source_uri: str | None = None


class GenerationResult(BaseModel):
    request_id: str
    job_id: str
    content_id: str
    generation_type: Literal["note"]
    status: Literal["completed"]
    created_at: str
    sources: list[GenerationSource]
    payload: NotePayload


class CliResponse(BaseModel):
    ok: bool
    command: str
    status: str
    message: str | None = None
    next_action: str | None = None
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
uv run pytest tests/test_generation_schema.py -v
```

Expected: 3 passed.

---

### Task 3: ID Generation

**Files:**
- Create: `kb/core/ids.py`
- Create: `tests/test_ids.py`

- [ ] **Step 1: Write ID tests**

```python
# tests/test_ids.py
from kb.core.ids import build_content_id, build_job_id, build_note_id, build_request_id


def test_content_and_note_ids_use_same_date_hash():
    content_id = build_content_id("20260618", "https://example.com/article")
    note_id = build_note_id("20260618", "https://example.com/article")

    assert content_id.startswith("cnt_20260618_")
    assert note_id.startswith("note_20260618_")
    assert content_id.split("_")[-1] == note_id.split("_")[-1]


def test_job_and_request_ids_include_timestamp_and_type():
    source = "https://example.com/article"

    job_id = build_job_id("20260618143022", source)
    request_id = build_request_id("20260618143022", source, "note")

    assert job_id.startswith("job_20260618143022_")
    assert request_id.startswith("gen_20260618143022_")
    assert request_id.endswith("_note")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_ids.py -v
```

Expected: FAIL because `kb.core.ids` does not exist.

- [ ] **Step 3: Implement ID helpers**

```python
# kb/core/ids.py
from hashlib import sha256


def source_key_hash(source_key: str) -> str:
    return sha256(source_key.encode("utf-8")).hexdigest()[:8]


def build_content_id(date_yyyymmdd: str, source_key: str) -> str:
    return f"cnt_{date_yyyymmdd}_{source_key_hash(source_key)}"


def build_note_id(date_yyyymmdd: str, source_key: str) -> str:
    return f"note_{date_yyyymmdd}_{source_key_hash(source_key)}"


def build_job_id(timestamp_yyyymmddhhmmss: str, source_key: str) -> str:
    return f"job_{timestamp_yyyymmddhhmmss}_{source_key_hash(source_key)}"


def build_request_id(timestamp_yyyymmddhhmmss: str, source_key: str, generation_type: str) -> str:
    return f"gen_{timestamp_yyyymmddhhmmss}_{source_key_hash(source_key)}_{generation_type}"
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
uv run pytest tests/test_ids.py -v
```

Expected: 2 passed.

---

### Task 4: Config Loader And Default Config

**Files:**
- Create: `kb.yaml`
- Create: `kb/config/__init__.py`
- Create: `kb/config/loader.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create default `kb.yaml`**

```yaml
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
```

- [ ] **Step 2: Write config tests**

```python
# tests/test_config.py
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
```

- [ ] **Step 3: Implement config loader**

```python
# kb/config/loader.py
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
```

- [ ] **Step 4: Run config tests**

Run:

```bash
uv run pytest tests/test_config.py -v
```

Expected: 1 passed.

---

### Task 5: Atomic Write And Locking

**Files:**
- Create: `kb/core/atomic.py`
- Create: `kb/core/locks.py`
- Create: `tests/test_atomic.py`

- [ ] **Step 1: Write atomic and lock tests**

```python
# tests/test_atomic.py
from pathlib import Path

import pytest

from kb.core.atomic import atomic_write_text
from kb.core.locks import IngestLockedError, ingest_lock


def test_atomic_write_text_writes_target(workspace: Path):
    target = workspace / "notes" / "note.md"

    atomic_write_text(target, "hello")

    assert target.read_text(encoding="utf-8") == "hello"
    assert not (workspace / "notes" / "note.md.tmp").exists()


def test_ingest_lock_rejects_existing_lock(workspace: Path):
    lock_path = workspace / "state" / "locks" / "ingest.lock"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("locked", encoding="utf-8")

    with pytest.raises(IngestLockedError):
        with ingest_lock(workspace):
            pass
```

- [ ] **Step 2: Implement atomic write**

```python
# kb/core/atomic.py
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)
```

- [ ] **Step 3: Implement lock context**

```python
# kb/core/locks.py
from contextlib import contextmanager
from pathlib import Path


class IngestLockedError(RuntimeError):
    pass


@contextmanager
def ingest_lock(root: Path):
    lock_path = root / "state" / "locks" / "ingest.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        raise IngestLockedError("Another ingest job is running.")
    lock_path.write_text("locked", encoding="utf-8")
    try:
        yield
    finally:
        if lock_path.exists():
            lock_path.unlink()
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_atomic.py -v
```

Expected: 2 passed.

---

### Task 6: Init Command

**Files:**
- Create: `kb/cli/commands/init.py`
- Modify: `kb/cli/main.py`
- Create: `tests/test_init_command.py`

- [ ] **Step 1: Write init command test**

```python
# tests/test_init_command.py
from typer.testing import CliRunner

from kb.cli.main import app


def test_init_creates_directories(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    result = CliRunner().invoke(app, ["init"])

    assert result.exit_code == 0
    assert '"status":"completed"' in result.stdout.replace(" ", "")
    for path in [
        "raw",
        "notes",
        "indexes",
        "prompts",
        "state/jobs",
        "state/generation_requests",
        "state/generation_results",
        "state/locks",
        "logs",
    ]:
        assert (workspace / path).exists()
```

- [ ] **Step 2: Implement init command**

```python
# kb/cli/commands/init.py
import json
from pathlib import Path

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def init() -> None:
    root = Path.cwd()
    for path in [
        "raw",
        "notes",
        "indexes",
        "prompts",
        "state/jobs",
        "state/generation_requests",
        "state/generation_results",
        "state/locks",
        "logs",
    ]:
        (root / path).mkdir(parents=True, exist_ok=True)
    typer.echo(json.dumps({"ok": True, "command": "kb init", "status": "completed", "next_action": "none"}, ensure_ascii=False))
```

- [ ] **Step 3: Register init command**

```python
# kb/cli/main.py
import typer

from kb.cli.commands import init

app = typer.Typer(no_args_is_help=True)
app.add_typer(init.app, name="init")


@app.callback()
def main() -> None:
    """Local AI knowledge base CLI."""
```

- [ ] **Step 4: Run test**

Run:

```bash
uv run pytest tests/test_init_command.py -v
```

Expected: 1 passed.

---

### Task 7: Storage Layer

**Files:**
- Create: `kb/storage/paths.py`
- Create: `kb/storage/job_store.py`
- Create: `kb/storage/generation_store.py`
- Create: `kb/storage/raw_store.py`
- Create: `kb/storage/note_store.py`
- Create: `kb/storage/index_store.py`

- [ ] **Step 1: Implement path helpers**

```python
# kb/storage/paths.py
from pathlib import Path


def dated_dir(root: Path, base: str, date_yyyymmdd: str) -> Path:
    return root / base / date_yyyymmdd
```

- [ ] **Step 2: Implement job store**

```python
# kb/storage/job_store.py
import json
from pathlib import Path
from typing import Any

from kb.core.atomic import atomic_write_text


def job_path(root: Path, job_id: str) -> Path:
    return root / "state" / "jobs" / f"{job_id}.json"


def write_job(root: Path, job_id: str, data: dict[str, Any]) -> Path:
    path = job_path(root, job_id)
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))
    return path


def read_job(root: Path, job_id: str) -> dict[str, Any]:
    return json.loads(job_path(root, job_id).read_text(encoding="utf-8"))
```

- [ ] **Step 3: Implement generation store**

```python
# kb/storage/generation_store.py
from pathlib import Path

import frontmatter
import yaml

from kb.core.atomic import atomic_write_text
from kb.core.models import GenerationResult


def request_path(root: Path, job_id: str, generation_type: str) -> Path:
    return root / "state" / "generation_requests" / f"{job_id}-{generation_type}.md"


def result_path(root: Path, job_id: str, generation_type: str) -> Path:
    return root / "state" / "generation_results" / f"{job_id}-{generation_type}.yaml"


def write_generation_request(root: Path, job_id: str, generation_type: str, metadata: dict, body: str) -> Path:
    path = request_path(root, job_id, generation_type)
    post = frontmatter.Post(body, **metadata)
    atomic_write_text(path, frontmatter.dumps(post))
    return path


def read_generation_result(root: Path, job_id: str, generation_type: str) -> GenerationResult:
    path = result_path(root, job_id, generation_type)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return GenerationResult.model_validate(data)
```

- [ ] **Step 4: Implement raw, note, and index stores**

```python
# kb/storage/raw_store.py
from pathlib import Path

from kb.core.atomic import atomic_write_text


def write_raw(root: Path, date_yyyymmdd: str, content_id: str, text: str, meta_yaml: str) -> tuple[Path, Path]:
    raw_dir = root / "raw" / date_yyyymmdd
    raw_path = raw_dir / f"{content_id}.md"
    meta_path = raw_dir / f"{content_id}.meta.yaml"
    atomic_write_text(raw_path, text)
    atomic_write_text(meta_path, meta_yaml)
    return raw_path, meta_path
```

```python
# kb/storage/note_store.py
from pathlib import Path

import frontmatter

from kb.core.atomic import atomic_write_text


def write_note(root: Path, date_yyyymmdd: str, note_id: str, metadata: dict, body: str) -> Path:
    path = root / "notes" / date_yyyymmdd / f"{note_id}.md"
    post = frontmatter.Post(body, **metadata)
    atomic_write_text(path, frontmatter.dumps(post))
    return path
```

```python
# kb/storage/index_store.py
from pathlib import Path

from kb.core.atomic import atomic_write_text


def write_phase1_indexes(root: Path, recent: str, tags: str, sources: str) -> list[Path]:
    index_dir = root / "indexes"
    paths = [
        index_dir / "recent.md",
        index_dir / "tags.md",
        index_dir / "sources.md",
    ]
    for path, content in zip(paths, [recent, tags, sources], strict=True):
        atomic_write_text(path, content)
    return paths
```

- [ ] **Step 5: Run existing tests**

Run:

```bash
uv run pytest -v
```

Expected: all existing tests pass.

---

### Task 8: Input Adapters

**Files:**
- Create: `kb/adapters/text.py`
- Create: `kb/adapters/files.py`
- Create: `kb/adapters/web.py`
- Create: `kb/adapters/registry.py`

- [ ] **Step 1: Implement direct text adapter**

```python
# kb/adapters/text.py
from pydantic import BaseModel


class AdaptedContent(BaseModel):
    source_type: str
    source_uri: str
    title: str
    text: str
    mime_type: str


def adapt_text(value: str) -> AdaptedContent:
    return AdaptedContent(
        source_type="text",
        source_uri=f"text:{value[:32]}",
        title="Direct Text",
        text=value,
        mime_type="text/plain",
    )
```

- [ ] **Step 2: Implement file adapters**

```python
# kb/adapters/files.py
from pathlib import Path

import fitz

from kb.adapters.text import AdaptedContent


def adapt_file(path: Path) -> AdaptedContent:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8")
    elif suffix == ".pdf":
        with fitz.open(path) as doc:
            text = "\n".join(page.get_text() for page in doc)
    else:
        raise ValueError("INVALID_INPUT")
    return AdaptedContent(
        source_type=suffix.removeprefix("."),
        source_uri=str(path.resolve()),
        title=path.stem,
        text=text,
        mime_type="application/pdf" if suffix == ".pdf" else "text/plain",
    )
```

- [ ] **Step 3: Implement generic web adapter**

```python
# kb/adapters/web.py
import httpx
import trafilatura

from kb.adapters.text import AdaptedContent


def adapt_web(url: str) -> AdaptedContent:
    response = httpx.get(url, timeout=20)
    response.raise_for_status()
    text = trafilatura.extract(response.text) or response.text
    return AdaptedContent(
        source_type="url",
        source_uri=url,
        title=url,
        text=text,
        mime_type="text/html",
    )
```

- [ ] **Step 4: Implement registry**

```python
# kb/adapters/registry.py
from pathlib import Path

from kb.adapters.files import adapt_file
from kb.adapters.text import adapt_text, AdaptedContent
from kb.adapters.web import adapt_web


def adapt_input(value: str) -> AdaptedContent:
    if value.startswith(("http://", "https://")):
        return adapt_web(value)
    path = Path(value)
    if path.exists():
        return adapt_file(path)
    return adapt_text(value)
```

- [ ] **Step 5: Run lint**

Run:

```bash
uv run ruff check kb/adapters
```

Expected: All checks passed.

---

### Task 9: Ingest First Pass

**Files:**
- Create: `kb/services/ingest_service.py`
- Create: `kb/cli/commands/ingest.py`
- Modify: `kb/cli/main.py`
- Create: `tests/test_ingest_flow.py`

- [ ] **Step 1: Write ingest first-pass test**

```python
# tests/test_ingest_flow.py
from typer.testing import CliRunner

from kb.cli.main import app


def test_ingest_text_creates_generation_request(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    CliRunner().invoke(app, ["init"])

    result = CliRunner().invoke(app, ["ingest", "AI 会改变个人知识管理"])

    assert result.exit_code == 0
    assert '"status":"needs_generation"' in result.stdout.replace(" ", "")
    assert (workspace / "state" / "generation_requests").exists()
    assert list((workspace / "state" / "generation_requests").glob("*.md"))
```

- [ ] **Step 2: Implement ingest first pass service**

```python
# kb/services/ingest_service.py
import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import yaml

from kb.adapters.registry import adapt_input
from kb.core.ids import build_content_id, build_job_id, build_request_id
from kb.core.locks import ingest_lock
from kb.storage.generation_store import result_path, write_generation_request
from kb.storage.job_store import write_job
from kb.storage.raw_store import write_raw


def _now() -> datetime:
    return datetime.now().astimezone()


def ingest_first_pass(root: Path, value: str) -> dict:
    with ingest_lock(root):
        now = _now()
        date = now.strftime("%Y%m%d")
        stamp = now.strftime("%Y%m%d%H%M%S")
        content = adapt_input(value)
        source_key = content.source_uri
        content_id = build_content_id(date, source_key)
        job_id = build_job_id(stamp, source_key)
        request_id = build_request_id(stamp, source_key, "note")
        content_hash = sha256(content.text.encode("utf-8")).hexdigest()
        raw_path, _ = write_raw(
            root,
            date,
            content_id,
            content.text,
            yaml.safe_dump(
                {
                    "id": content_id,
                    "source_type": content.source_type,
                    "source_uri": content.source_uri,
                    "source_title": content.title,
                    "captured_at": now.isoformat(),
                    "content_hash": f"sha256:{content_hash}",
                    "mime_type": content.mime_type,
                    "status": "active",
                },
                allow_unicode=True,
            ),
        )
        result = result_path(root, job_id, "note")
        request = write_generation_request(
            root,
            job_id,
            "note",
            {
                "request_id": request_id,
                "job_id": job_id,
                "content_id": content_id,
                "generation_type": "note",
                "source_paths": [str(raw_path.relative_to(root))],
                "prompt_path": "prompts/note.md",
                "output_schema": "note_v1",
                "result_path": str(result.relative_to(root)),
            },
            "## 任务\n\n请读取 `source_paths` 中的原文，生成一份结构化 note 结果。\n\n## 输出要求\n\n只写入 `result_path`，不要直接修改 `notes/`、`indexes/`、`wiki/`。\n",
        )
        write_job(
            root,
            job_id,
            {
                "job_id": job_id,
                "content_id": content_id,
                "status": "needs_generation",
                "current_stage": "generation_requested",
                "completed_stages": ["received", "raw_saved", "generation_requested"],
                "retry_count": 0,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            },
        )
        return {
            "ok": True,
            "command": "kb ingest",
            "status": "needs_generation",
            "job_id": job_id,
            "content_id": content_id,
            "next_action": "write_generation_result",
            "generation_request_path": str(request.relative_to(root)),
            "generation_result_path": str(result.relative_to(root)),
            "message": "Generation request created. Read request file and write result file.",
        }
```

- [ ] **Step 3: Add ingest command**

```python
# kb/cli/commands/ingest.py
import json
from pathlib import Path

import typer

from kb.services.ingest_service import ingest_first_pass

app = typer.Typer()


@app.callback(invoke_without_command=True)
def ingest(input_value: str = typer.Argument(...)) -> None:
    response = ingest_first_pass(Path.cwd(), input_value)
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
```

- [ ] **Step 4: Register ingest command**

```python
# kb/cli/main.py
import typer

from kb.cli.commands import ingest, init

app = typer.Typer(no_args_is_help=True)
app.add_typer(init.app, name="init")
app.add_typer(ingest.app, name="ingest")


@app.callback()
def main() -> None:
    """Local AI knowledge base CLI."""
```

- [ ] **Step 5: Run ingest test**

Run:

```bash
uv run pytest tests/test_ingest_flow.py::test_ingest_text_creates_generation_request -v
```

Expected: 1 passed.

---

### Task 10: Ingest Continue

**Files:**
- Modify: `kb/services/ingest_service.py`
- Modify: `kb/cli/commands/ingest.py`
- Modify: `tests/test_ingest_flow.py`

- [ ] **Step 1: Add continue test**

Append to `tests/test_ingest_flow.py`:

```python
import json
import yaml


def test_ingest_continue_writes_note_and_indexes(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    first = runner.invoke(app, ["ingest", "AI 会改变个人知识管理"])
    data = json.loads(first.stdout)
    result_path = workspace / data["generation_result_path"]
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        yaml.safe_dump(
            {
                "request_id": "gen_20260618143022_a8f31c92_note",
                "job_id": data["job_id"],
                "content_id": data["content_id"],
                "generation_type": "note",
                "status": "completed",
                "created_at": "2026-06-18T14:32:00+08:00",
                "sources": [{"path": "raw/20260618/example.md", "source_uri": "text:test"}],
                "payload": {
                    "title": "AI 知识管理",
                    "summary": "AI 能提升个人知识管理效率。",
                    "tags": ["ai", "knowledge", "workflow"],
                    "stance": "approve",
                    "key_points": ["更快整理", "更容易检索", "更适合写作"],
                    "my_judgement": "值得纳入知识库。",
                    "useful_for": ["写作", "选题"],
                    "related_topics": ["ai-knowledge-base"],
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    second = runner.invoke(app, ["ingest", "--continue-job", data["job_id"]])

    assert second.exit_code == 0
    assert '"status":"completed"' in second.stdout.replace(" ", "")
    assert list((workspace / "notes").glob("**/*.md"))
    assert (workspace / "indexes" / "recent.md").exists()
```

- [ ] **Step 2: Implement continue service**

Append to `kb/services/ingest_service.py`:

```python
import frontmatter

from kb.core.ids import build_note_id
from kb.storage.generation_store import read_generation_result
from kb.storage.index_store import write_phase1_indexes
from kb.storage.job_store import read_job
from kb.storage.note_store import write_note


def ingest_continue(root: Path, job_id: str) -> dict:
    job = read_job(root, job_id)
    result = read_generation_result(root, job_id, "note")
    date = result.content_id.split("_")[1]
    source_key = result.content_id
    note_id = build_note_id(date, source_key)
    metadata = {
        "id": note_id,
        "content_id": result.content_id,
        "title": result.payload.title,
        "source_type": "text",
        "source_uri": result.sources[0].source_uri,
        "created_at": result.created_at,
        "tags": result.payload.tags,
        "summary": result.payload.summary,
        "stance": result.payload.stance.value,
        "related_note_ids": [],
        "topic_keys": [],
        "status": "active",
    }
    body = "\n\n".join(
        [
            f"## 摘要\n\n{result.payload.summary}",
            "## 关键信息\n\n" + "\n".join(f"- {item}" for item in result.payload.key_points),
            f"## 我的判断\n\n{result.payload.my_judgement}",
            "## 可用场景\n\n" + "\n".join(f"- {item}" for item in result.payload.useful_for),
            "## 主题候选\n\n" + "\n".join(f"- {item}" for item in result.payload.related_topics),
        ]
    )
    note_path = write_note(root, date, note_id, metadata, body)
    index_paths = write_phase1_indexes(
        root,
        f"# Recent\n\n- [{result.payload.title}]({note_path.as_posix()})\n",
        "# Tags\n\n" + "\n".join(f"- {tag}: {note_id}" for tag in result.payload.tags) + "\n",
        f"# Sources\n\n- {result.sources[0].source_uri}: {note_id}\n",
    )
    write_job(
        root,
        job_id,
        {
            **job,
            "status": "completed",
            "current_stage": "completed",
            "completed_stages": [*job.get("completed_stages", []), "generation_completed", "note_generated", "indexes_updated", "completed"],
            "updated_at": _now().isoformat(),
        },
    )
    return {
        "ok": True,
        "command": "kb ingest --continue",
        "status": "completed",
        "job_id": job_id,
        "note_path": str(note_path.relative_to(root)),
        "index_paths": [str(path.relative_to(root)) for path in index_paths],
        "next_action": "none",
        "message": "Note persisted and indexes updated.",
    }
```

- [ ] **Step 3: Update ingest command for continue**

```python
# kb/cli/commands/ingest.py
import json
from pathlib import Path

import typer

from kb.services.ingest_service import ingest_continue, ingest_first_pass

app = typer.Typer()


@app.callback(invoke_without_command=True)
def ingest(
    input_value: str | None = typer.Argument(None),
    continue_job: str | None = typer.Option(None, "--continue-job"),
) -> None:
    if continue_job:
        response = ingest_continue(Path.cwd(), continue_job)
    elif input_value:
        response = ingest_first_pass(Path.cwd(), input_value)
    else:
        response = {
            "ok": False,
            "command": "kb ingest",
            "status": "permanent_failed",
            "error_code": "INVALID_INPUT",
            "error_message": "input_value or --continue-job is required",
            "retryable": False,
            "next_action": "none",
        }
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
```

- [ ] **Step 4: Run flow test**

Run:

```bash
uv run pytest tests/test_ingest_flow.py -v
```

Expected: 2 passed.

---

### Task 11: Ask Scoring And Command

**Files:**
- Create: `kb/core/scoring.py`
- Create: `kb/services/ask_service.py`
- Create: `kb/cli/commands/ask.py`
- Modify: `kb/cli/main.py`
- Create: `tests/test_ask_scoring.py`

- [ ] **Step 1: Write scoring test**

```python
# tests/test_ask_scoring.py
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
```

- [ ] **Step 2: Implement scoring**

```python
# kb/core/scoring.py
def _contains_any(query_terms: list[str], value: str) -> bool:
    lower = value.lower()
    return any(term.lower() in lower for term in query_terms)


def score_note(query: str, note: dict) -> int:
    terms = [term for term in query.split() if term]
    score = 0
    if _contains_any(terms, note.get("title", "")):
        score += 5
    if any(_contains_any(terms, tag) for tag in note.get("tags", [])):
        score += 4
    if _contains_any(terms, note.get("summary", "")):
        score += 3
    if _contains_any(terms, note.get("body", "")):
        score += 2
    if _contains_any(terms, note.get("source_uri", "")):
        score += 1
    return score
```

- [ ] **Step 3: Implement ask service**

```python
# kb/services/ask_service.py
from pathlib import Path

import frontmatter

from kb.core.scoring import score_note


def ask(root: Path, question: str, max_notes: int = 5, min_score: int = 1) -> dict:
    hits = []
    for path in (root / "notes").glob("**/*.md"):
        post = frontmatter.loads(path.read_text(encoding="utf-8"))
        note = {
            "title": post.metadata.get("title", ""),
            "tags": post.metadata.get("tags", []),
            "summary": post.metadata.get("summary", ""),
            "body": post.content,
            "source_uri": post.metadata.get("source_uri", ""),
        }
        score = score_note(question, note)
        if score >= min_score:
            hits.append(
                {
                    "score": score,
                    "note_path": str(path.relative_to(root)),
                    "title": note["title"],
                    "summary": note["summary"],
                    "source_uri": note["source_uri"],
                }
            )
    hits.sort(key=lambda item: item["score"], reverse=True)
    return {
        "ok": True,
        "command": "kb ask",
        "status": "completed",
        "question": question,
        "notes": hits[:max_notes],
        "next_action": "none",
        "message": "Matched notes returned. Agent should compose answer with citations.",
    }
```

- [ ] **Step 4: Add ask command and register**

```python
# kb/cli/commands/ask.py
import json
from pathlib import Path

import typer

from kb.services.ask_service import ask as ask_service

app = typer.Typer()


@app.callback(invoke_without_command=True)
def ask(question: str = typer.Argument(...)) -> None:
    response = ask_service(Path.cwd(), question)
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
```

Update `kb/cli/main.py`:

```python
import typer

from kb.cli.commands import ask, ingest, init

app = typer.Typer(no_args_is_help=True)
app.add_typer(init.app, name="init")
app.add_typer(ingest.app, name="ingest")
app.add_typer(ask.app, name="ask")


@app.callback()
def main() -> None:
    """Local AI knowledge base CLI."""
```

- [ ] **Step 5: Run ask tests and full tests**

Run:

```bash
uv run pytest tests/test_ask_scoring.py -v
uv run pytest -v
```

Expected: all tests pass.

---

### Task 12: Error Handling And JSON Failures

**Files:**
- Create: `kb/core/errors.py`
- Modify: `kb/cli/commands/ingest.py`
- Modify: `kb/services/ingest_service.py`

- [ ] **Step 1: Implement error response helper**

```python
# kb/core/errors.py
def error_response(
    command: str,
    status: str,
    error_code: str,
    error_message: str,
    retryable: bool,
    next_action: str,
    job_id: str | None = None,
) -> dict:
    data = {
        "ok": False,
        "command": command,
        "status": status,
        "error_code": error_code,
        "error_message": error_message,
        "retryable": retryable,
        "next_action": next_action,
    }
    if job_id:
        data["job_id"] = job_id
    return data
```

- [ ] **Step 2: Catch missing generation result**

In `kb/services/ingest_service.py`, wrap `read_generation_result` errors:

```python
from pydantic import ValidationError

from kb.core.errors import error_response


def ingest_continue(root: Path, job_id: str) -> dict:
    job = read_job(root, job_id)
    try:
        result = read_generation_result(root, job_id, "note")
    except FileNotFoundError:
        return error_response(
            command="kb ingest --continue",
            status="failed",
            error_code="GENERATION_RESULT_NOT_FOUND",
            error_message="Generation result file does not exist.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    except ValidationError as exc:
        return error_response(
            command="kb ingest --continue",
            status="failed",
            error_code="GENERATION_RESULT_INVALID",
            error_message=str(exc),
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    # keep the existing success implementation below this point
```

- [ ] **Step 3: Run tests**

Run:

```bash
uv run pytest -v
```

Expected: all tests pass.

---

### Task 13: Final Verification

**Files:**
- Modify: none unless verification exposes a real gap

- [ ] **Step 1: Run all tests**

Run:

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run lint**

Run:

```bash
uv run ruff check .
```

Expected: All checks passed.

- [ ] **Step 3: Run manual smoke test**

Run:

```bash
uv run kb init
uv run kb ingest "AI 会改变个人知识管理"
```

Expected first command JSON:

```json
{"ok":true,"command":"kb init","status":"completed","next_action":"none"}
```

Expected second command JSON contains:

```json
"status":"needs_generation"
```

- [ ] **Step 4: Verify generated files**

Run:

```bash
Get-ChildItem -Recurse state,generation_requests,raw
```

On PowerShell, if `generation_requests` is not a root path, use:

```bash
Get-ChildItem -Recurse state,raw
```

Expected:

- `state/jobs/*.json`
- `state/generation_requests/*.md`
- `raw/YYYYMMDD/*.md`
- `raw/YYYYMMDD/*.meta.yaml`

- [ ] **Step 5: Record checkpoint**

If this workspace is a git repository, run:

```bash
git status --short
git add pyproject.toml kb.yaml kb tests
git commit -m "feat: implement phase1 knowledge base cli"
```

If this workspace is not a git repository, record completion in the implementation handoff instead of running git commands.

---

## Self-Review

Spec coverage:

- Phase 1 CLI commands are covered by Tasks 1, 6, 9, 10, 11.
- ID, schema, request/result, JSON stdout, lock, atomic write, errors, config, input adapters, indexes, and ask scoring are covered.
- Topic compiler and brief are intentionally excluded from Phase 1.
- GitHub and WeChat dedicated adapters are intentionally excluded from Phase 1.

Placeholder scan:

- No placeholder markers or unspecified error-handling instructions are present.
- Each implementation task includes concrete files, code snippets, commands, and expected results.

Type consistency:

- `GenerationResult.payload` uses the confirmed `NotePayload` schema.
- CLI status and `next_action` values match the confirmed enums.
- File paths match the confirmed Phase 1 layout.
