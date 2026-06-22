# 知识库使用规则

## 目标

本目录是个人知识库工作区。这里包含知识库功能代码、配置、数据和智能体使用协议。

## 目录边界

- `kb/`：知识库功能代码。只有用户要求改功能、修 bug、跑测试时才修改。
- `kb.yaml`：知识库配置。
- `prompts/`：生成 note、topic、brief 使用的 prompt。
- `raw/`：原始资料。
- `notes/`：原子笔记。
- `wiki/`：主题页。
- `briefs/`：选题和周报。
- `indexes/`：索引。
- `state/`：job、generation request/result。
- `logs/`：运行日志。
- `docs/`：智能体使用协议和知识库操作说明。

## 使用规则

- 入库使用 `uv run kb ingest <input>`。
- 查询使用 `uv run kb ask "<question>"`。
- 主题编译继续执行使用 `uv run kb compile --continue <job_id> --topic-key <topic_key>`。
- 生成选题使用 `uv run kb brief topics`。
- 生成周报使用 `uv run kb brief weekly`。
- 遇到 `needs_generation` 时，智能体读取 generation request，写入 generation result，再执行对应 `--continue`。
- 不直接手改 `raw/`、`notes/`、`wiki/`、`briefs/`、`indexes/`、`state/`，除非用户明确要求修复数据。

## 开发边界

- 修改 `kb/` 属于功能开发，不属于普通知识库使用。
- 修改 `kb/` 后必须回到仓库外层运行 `uv run pytest -q` 和 `uv run ruff check .`。
