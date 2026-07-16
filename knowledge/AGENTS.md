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
- `wiki/insight-*.md`：用户明确要求保存的问答结论。
- `briefs/`：选题和周报。
- `indexes/`：索引。
- `state/`：job、generation request/result。
- `reports/`：知识库健康检查报告，只保存检查结果，不自动修改知识内容。
- `logs/history.md`：知识库演化记录，按时间追加 ingest、compile、ask、lint、brief 等成功操作。
- `docs/`：智能体使用协议和知识库操作说明。

## 使用规则

- 入库使用 `uv run kb ingest <input>`。
- 盘点知识库内容、数量、标签、来源使用 `uv run kb status`。
- 查询具体主题、观点、概念使用 `uv run kb ask "<question>"`，得到生成请求后写入结果，再执行 `uv run kb ask --continue <job_id>`。
- 只有用户明确要求沉淀问答时才使用 `uv run kb ask "<question>" --save`，继续执行后写入 `wiki/insight-*.md`。
- 主动编译或重新编译主题使用 `uv run kb compile --topic-key <topic_key>`。
- 主题编译继续执行使用 `uv run kb compile --continue <job_id> --topic-key <topic_key>`。
- 知识健康检查使用 `uv run kb lint`，写入结果后执行 `uv run kb lint --continue <job_id>`；Lint 只生成报告，不自动改 Wiki。
- 生成选题使用 `uv run kb brief topics`。
- 生成周报使用 `uv run kb brief weekly`。
- 遇到 `needs_generation` 时，智能体读取 generation request，写入 generation result，再执行对应 `--continue`。
- Answer 的引用必须来自 generation request 提供的 `source_paths`，不得编造来源。
- Lint 报告建议重编译主题时，必须由用户或智能体显式执行 `kb compile --topic-key <topic_key>`。
- 回答“当前知识库有哪些内容”这类盘点问题时，不全局搜索 `knowledge/`；优先使用 `kb status`，命令不可用时只读 `indexes/recent.md`、`indexes/tags.md`、`indexes/sources.md`。
- 只有索引缺失或损坏时，才允许只读检查 `notes/**/*.md` 作为兜底，并在回复中说明兜底原因。
- 不直接手改 `raw/`、`notes/`、`wiki/`、`briefs/`、`indexes/`、`reports/`、`state/`，除非用户明确要求修复数据；generation result 仍按请求路径写入。

## 开发边界

- 修改 `kb/` 属于功能开发，不属于普通知识库使用。
- 修改 `kb/` 后必须回到仓库外层运行 `uv run pytest -q` 和 `uv run ruff check .`。
