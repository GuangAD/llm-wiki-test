# Knowledge Compile And Briefs Implementation Plan

> 归档说明：本文是迁移前的功能实施计划。文中的 `kb/`、`raw/`、`notes/`、`indexes/`、`prompts/`、`state/` 等路径按当时“仓库根目录即知识库根目录”的结构描述；当前结构已调整为功能代码位于 `knowledge/kb/`，知识库运行目录位于 `knowledge/` 下。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现关联关系构建、`wiki/` 主题页编译、`brief topics` 和 `brief weekly`，让知识库从 Phase 1 的原子笔记查询进入 Phase 2/3 的主题编译和反向产出。

**Architecture:** 延续当前本地 CLI + 文件存储架构。代码只负责确定性工作：读取 note、计算关联分数、写回 frontmatter、生成结构化请求、校验结果、落盘主题页和 brief；摘要、主题结论、选题文案和周报文案仍由智能体通过 `state/generation_requests/` 与 `state/generation_results/` 交接完成。

**Tech Stack:** Python 3.12、Typer、Pydantic、python-frontmatter、PyYAML、pytest。

---

## 范围

### 本次实现

- `kb ingest --continue <job_id>` 写入 note 后自动构建轻量关联关系。
- 达到主题创建条件时生成 `topic` 类型的 GenerationRequest。
- 新增 `kb compile --continue <job_id> --topic-key <topic_key>`，读取智能体生成结果并写入 `wiki/topic-<topic_key>.md`。
- 新增 `indexes/topics.md`。
- 新增 `kb brief topics`，生成选题 brief 请求。
- 新增 `kb brief topics --continue <job_id>`，读取结果并写入 `briefs/topic-picks-YYYYMMDD.md`。
- 新增 `kb brief weekly`，生成周报 brief 请求。
- 新增 `kb brief weekly --continue <job_id>`，读取结果并写入 `briefs/weekly-YYYY-WW.md`。

### 本次不做

- 不接入 LLM API。
- 不引入数据库或向量库。
- 不做后台队列、异步执行或多进程并发。
- 不做 Web UI。
- 不自动删除或重写 `raw/`。

## 成功标准

- `pytest` 全量通过。
- `kb init` 会创建 `wiki/`、`briefs/`，并初始化 `prompts/topic.md`、`prompts/brief-topics.md`、`prompts/brief-weekly.md`。
- 入库第二条同主题 note 后，相关 note 的 `related_note_ids` 能互相写回。
- 满足至少 2 条 note 的主题会产生 topic 编译请求。
- 写入合法 topic 生成结果后，`wiki/topic-<topic_key>.md` 和 `indexes/topics.md` 被更新。
- `brief topics` 和 `brief weekly` 都遵循“先生成请求，智能体写结果，再 continue 落盘”的协议。
- 所有新增 CLI 默认输出 JSON。

## 文件结构

- Modify: `kb/cli/main.py`
  - 注册 `compile` 与 `brief` 命令。
- Modify: `kb/cli/commands/init.py`
  - 增加运行目录和默认 prompt。
- Modify: `kb/cli/commands/ingest.py`
  - 保持入口不变，底层 continue 增加 relation/topic 请求结果字段。
- Create: `kb/cli/commands/compile.py`
  - 处理 topic 编译结果落盘。
- Create: `kb/cli/commands/brief.py`
  - 提供 `topics`、`weekly` 及各自 `--continue`。
- Modify: `kb/core/models.py`
  - 增加 `TopicPayload`、`BriefTopicsPayload`、`BriefWeeklyPayload`、扩展 `GenerationResult.generation_type`。
- Modify: `kb/core/scoring.py`
  - 复用或新增 note 关联分数函数。
- Create: `kb/core/topics.py`
  - `slugify_topic_key()`、`extract_topic_keys()` 等确定性主题 key 工具。
- Modify: `kb/storage/generation_store.py`
  - 支持不同 `generation_type` 的请求与结果读取。
- Modify: `kb/storage/note_store.py`
  - 增加读取全部 note、按路径写回 frontmatter 的能力。
- Create: `kb/storage/topic_store.py`
  - 写入 `wiki/topic-<topic_key>.md`。
- Create: `kb/storage/brief_store.py`
  - 写入 `briefs/topic-picks-YYYYMMDD.md`、`briefs/weekly-YYYY-WW.md`。
- Modify: `kb/storage/index_store.py`
  - 增加 `topics.md` 写入。
- Create: `kb/services/relation_service.py`
  - 构建 note 之间的双向关联和 topic 候选。
- Create: `kb/services/topic_service.py`
  - 生成 topic request，继续 topic 落盘，更新 topic index。
- Create: `kb/services/brief_service.py`
  - 生成 brief request，继续 brief 落盘。
- Modify: `kb/services/ingest_service.py`
  - `ingest_continue()` 在 note 写入后调用 relation 和 topic request 逻辑。
- Tests:
  - `tests/test_relation_service.py`
  - `tests/test_topic_compile_flow.py`
  - `tests/test_brief_flow.py`
  - 更新 `tests/test_init_command.py`
  - 更新 `tests/test_ingest_flow.py`

## 数据协议

### topic_v1 GenerationResult

```yaml
request_id: gen_20260622100000_ai-knowledge-base_topic
job_id: job_20260622100000_ai-knowledge-base
generation_type: topic
status: completed
created_at: 2026-06-22T10:00:00+08:00
sources:
  - path: notes/20260618/note_20260618_a.md
payload:
  topic_key: ai-knowledge-base
  title: AI 知识库
  definition: 这个主题讨论什么
  conclusions:
    - 已形成的主要结论
  disagreements:
    - 关键分歧或未决问题
  extensions:
    - 可延伸方向
  source_note_ids:
    - note_20260618_a
```

### brief_topics_v1 GenerationResult

```yaml
request_id: gen_20260622100000_brief_topics
job_id: job_20260622100000_brief_topics
generation_type: brief_topics
status: completed
created_at: 2026-06-22T10:00:00+08:00
sources:
  - path: indexes/recent.md
payload:
  date: 2026-06-22
  topics:
    - title: AI 知识库为什么不该一上来做向量库
      reason: 多条笔记都指向文件化和可追溯优先
      angle: 从反过度工程切入
      source_note_ids:
        - note_20260618_a
```

### brief_weekly_v1 GenerationResult

```yaml
request_id: gen_20260622100000_brief_weekly
job_id: job_20260622100000_brief_weekly
generation_type: brief_weekly
status: completed
created_at: 2026-06-22T10:00:00+08:00
sources:
  - path: indexes/recent.md
payload:
  week: 2026-W26
  new_items:
    - AI 知识库架构
  key_themes:
    - AI Native 知识库
  open_questions:
    - 是否需要引入主题页版本记录
  next_actions:
    - 整理 AI 知识库主题页
```

## 实施任务

### Task 1: 扩展初始化目录与 prompt

- [ ] 更新 `RUNTIME_DIRS`，新增 `wiki`、`briefs`。
- [ ] 新增默认 prompt 常量：`TOPIC_PROMPT`、`BRIEF_TOPICS_PROMPT`、`BRIEF_WEEKLY_PROMPT`。
- [ ] `kb init` 在 prompt 不存在时写入 4 个 prompt 文件。
- [ ] 更新 `tests/test_init_command.py`，断言新增目录和 prompt 存在。
- [ ] 验证：`pytest tests/test_init_command.py -v`。

### Task 2: 扩展生成结果 schema

- [ ] 在 `kb/core/models.py` 增加 topic 和 brief payload 模型。
- [ ] `GenerationResult.generation_type` 支持 `note | topic | brief_topics | brief_weekly`。
- [ ] 对不同 `generation_type` 使用 discriminated union 或手动校验，避免 `topic` 结果误用 `NotePayload`。
- [ ] 新增 `tests/test_generation_schema.py` 用例覆盖 4 种结果。
- [ ] 验证：`pytest tests/test_generation_schema.py -v`。

### Task 3: 实现关联关系构建

- [ ] 新建 `kb/services/relation_service.py`。
- [ ] 关联规则：标签重叠 + 标题关键词重叠，分数达到阈值才关联。
- [ ] 双向写回 `related_note_ids`，只写因当前 note 触发的相关 note。
- [ ] `topic_keys` 从 `related_topics` 归一化得到，至少两个 note 命中同一 topic_key 才作为可编译主题。
- [ ] 新增 `tests/test_relation_service.py`，覆盖双向关联、低分不关联、topic_key 稳定。
- [ ] 验证：`pytest tests/test_relation_service.py -v`。

### Task 4: 在 ingest continue 后接入 relation/topic request

- [ ] `ingest_continue()` 写入 note 后调用 relation service。
- [ ] 如果存在满足条件的 topic_key，生成 `topic` GenerationRequest。
- [ ] 返回 JSON 增加 `related_note_ids`、`topic_request_paths`、`next_action`。
- [ ] Phase 1 索引继续更新，新增 topic request 不阻塞 note 完成。
- [ ] 更新 `tests/test_ingest_flow.py`。
- [ ] 验证：`pytest tests/test_ingest_flow.py -v`。

### Task 5: 实现 topic 编译落盘

- [ ] 新建 `kb/cli/commands/compile.py`。
- [ ] 新建 `kb/services/topic_service.py`。
- [ ] 新建 `kb/storage/topic_store.py`。
- [ ] `kb compile --continue <job_id> --topic-key <topic_key>` 读取 `topic` result，校验 payload.topic_key 与参数一致，写入 `wiki/topic-<topic_key>.md`。
- [ ] 更新 `indexes/topics.md`。
- [ ] 新增 `tests/test_topic_compile_flow.py`。
- [ ] 验证：`pytest tests/test_topic_compile_flow.py -v`。

### Task 6: 实现 brief topics

- [ ] 新建 `kb/cli/commands/brief.py`。
- [ ] 新建 `kb/services/brief_service.py`。
- [ ] 新建 `kb/storage/brief_store.py`。
- [ ] `kb brief topics` 生成 `brief_topics` GenerationRequest，读取范围包含 `indexes/recent.md`、`indexes/tags.md`、`indexes/topics.md`、必要 note/wiki 路径。
- [ ] `kb brief topics --continue <job_id>` 写入 `briefs/topic-picks-YYYYMMDD.md`。
- [ ] 新增 `tests/test_brief_flow.py` 的 topics 用例。
- [ ] 验证：`pytest tests/test_brief_flow.py::test_brief_topics_flow -v`。

### Task 7: 实现 brief weekly

- [ ] `kb brief weekly` 生成 `brief_weekly` GenerationRequest，默认当前自然周。
- [ ] `kb brief weekly --continue <job_id>` 写入 `briefs/weekly-YYYY-WW.md`。
- [ ] `payload.week` 必须与命令目标周一致。
- [ ] 新增 `tests/test_brief_flow.py` 的 weekly 用例。
- [ ] 验证：`pytest tests/test_brief_flow.py::test_brief_weekly_flow -v`。

### Task 8: 全量验证与文档对齐

- [ ] 运行 `pytest -v`。
- [ ] 运行 `ruff check .`。
- [ ] 如 CLI 协议和 `docs/AI知识库技术架构文档.md` 有偏差，只更新与本次功能直接相关的小节。
- [ ] 对照检查没有触碰 `.env`、密钥、数据库、发布动作、删除文件。

## 风险与取舍

- 关联关系先用确定性轻量算法，不做语义相似度，符合当前“不上向量库”的约束。
- topic/brief 文案仍通过智能体生成，保持项目既定边界，避免在代码里伪造语义结论。
- `ingest --continue` 不等待 topic 编译完成；note 入库完成就是完成，topic 是后续增强链路。
- brief 命令先采用生成请求/继续落盘两段式，和 note/topic 保持一致。

## 执行前确认点

1. `brief topics`、`brief weekly` 是否接受两段式交互：先生成 request，再由智能体写 result，然后 `--continue` 落盘。
2. topic 编译入口是否接受命名为 `kb compile --continue ...`，而不是放在 `kb ingest --continue` 里自动完成。
3. 关联算法首版是否只用标签和标题关键词，不做正文全文匹配。
