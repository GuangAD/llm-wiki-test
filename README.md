# fuxi-kb

个人 AI 知识库工作区与功能代码。

## 目录边界

- 外层：开发知识库系统，包含 `pyproject.toml`、`uv.lock`、`tests/`、`docs/`。
- `knowledge/`：实际知识库工作区，包含功能代码、配置、数据和智能体使用规则。

## 常用命令

开发验证在外层执行：

```powershell
uv run pytest -q
uv run ruff check .
```

知识库使用在 `knowledge/` 内执行：

```powershell
uv run kb ingest "<input>"
uv run kb status
uv run kb ask "<question>"
uv run kb ask --continue <job_id>
uv run kb compile --topic-key <topic_key>
uv run kb lint
uv run kb brief topics
uv run kb brief weekly
```
