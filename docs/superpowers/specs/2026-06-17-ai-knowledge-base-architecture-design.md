# AI 知识库架构设计

## 1. 目标

为个人 AI 知识库 MVP 定义一套可直接实现的本地架构。该架构必须满足：

- 单人自用
- 本地运行
- 纯文件存储
- 全同步 `ingest`
- 内容与执行状态分离
- 问答、选题、周报三类输出可稳定运行

这不是通用平台架构，而是一个本地知识编译系统架构。

## 2. 总体定位

系统以 `kb` 作为统一 CLI 入口，以文件系统作为主存储，以 `job state` 作为执行状态存储，以 `topic page` 作为主要知识出口，以 `indexes` 作为导航层。

核心定义：

- 写路径唯一：所有写操作通过 `kb ingest` 和受控维护命令进入
- 读路径只读：`kb ask`、`kb brief` 不允许写库
- 智能体生成结构化：所有生成结果必须先过 schema 校验，再落盘
- 主题页优先：问答先读主题页，再回退原子笔记

## 3. 总体架构

推荐采用“管道编排 + 明确模块边界”方案。

### 3.1 写入链路

```text
kb ingest
  -> source adapter
  -> raw persistence
  -> note builder
  -> relation builder
  -> topic compiler
  -> index builder
  -> job finalize
```

### 3.2 读取链路

```text
kb ask
  -> query parser
  -> indexes lookup
  -> topic pages first
  -> notes fallback
  -> answer with citations
```

### 3.3 输出链路

```text
kb brief topics / weekly
  -> indexes + wiki + notes
  -> brief compiler
  -> briefs output
```

## 4. 运行边界

- 单进程
- 串行执行
- 显式命令触发
- 不做后台常驻 worker
- 不做自动定时任务
- 同一时刻只允许一个 `kb ingest`

这样做是为了避免文件系统并发写带来的状态脏写问题，并保持全同步 ingest 的可追踪性。

## 5. 存储结构

```text
project-root/
  raw/
  notes/
  wiki/
  indexes/
  briefs/
  prompts/
  state/
  logs/
  scripts/
  docs/
```

### 5.1 目录职责

- `raw/`：原始资料归档，只追加，不覆盖
- `notes/`：原子笔记，是单条素材的 AI 理解结果
- `wiki/`：主题页，是多条笔记编译后的知识出口
- `indexes/`：导航索引，只做定位，不承载结论
- `briefs/`：选题、周报等输出内容
- `prompts/`：Prompt 模板、标签体系、固定规则
- `state/`：任务状态、失败信息、重试记录
- `logs/`：运行日志

## 6. 核心数据对象

程序内部必须先把文件转换成标准对象，再在模块间传递，不允许模块直接绕过对象层随意改文件。

### 6.1 Content

表示标准化后的输入内容。

核心字段：

- `content_id`
- `source_type`
- `source_uri`
- `raw_text` 或原始文件路径
- `meta`

### 6.2 Note

表示原子笔记。

核心字段：

- `note_id`
- `content_id`
- `title`
- `tags`
- `summary`
- `stance`
- `related_note_ids`
- `topic_keys`

### 6.3 Topic

表示主题页。

核心字段：

- `topic_key`
- `title`
- `source_note_ids`
- `updated_at`
- `summary_sections`

### 6.4 Job

表示一次 ingest 任务。

核心字段：

- `job_id`
- `content_id`
- `current_stage`
- `completed_stages`
- `retry_count`
- `status`

## 7. 文件格式约定

### 7.1 ID 与文件命名规则

ID 采用“日期 + 短 hash”，不使用自增序号。

规则：

- `content_id`：`cnt_<YYYYMMDD>_<source_key_hash>`
- `note_id`：`note_<YYYYMMDD>_<source_key_hash>`
- `job_id`：`job_<YYYYMMDDHHMMSS>_<source_key_hash>`
- `request_id`：`gen_<YYYYMMDDHHMMSS>_<source_key_hash>_<generation_type>`

`source_key_hash` 取前 8 位，来源如下：

- URL：标准化后的 `source_uri`
- 本地文件：绝对文件路径 + 文件内容 hash
- 纯文本：文本内容 hash

文件命名：

- `raw/YYYYMMDD/<content_id>.md`
- `raw/YYYYMMDD/<content_id>.meta.yaml`
- `notes/YYYYMMDD/<note_id>.md`
- `state/jobs/<job_id>.json`
- `state/generation_requests/<job_id>-<generation_type>.md`
- `state/generation_results/<job_id>-<generation_type>.yaml`

示例：

```text
content_id: cnt_20260618_a8f31c92
note_id: note_20260618_a8f31c92
job_id: job_20260618143022_a8f31c92
request_id: gen_20260618143022_a8f31c92_note
```

### 7.2 raw

建议拆成正文文件和元数据文件：

- `raw/YYYYMMDD/<content_id>.md` 或原始 PDF/文本副本
- `raw/YYYYMMDD/<content_id>.meta.yaml`

元数据最少字段：

```yaml
id: cnt_20260618_a8f31c92
source_type: url
source_uri: https://example.com/article
source_title: Example Title
captured_at: 2026-06-18T14:30:00+08:00
content_hash: sha256:...
mime_type: text/html
status: active
```

### 7.3 note

文件命名：`notes/YYYYMMDD/<note_id>.md`

frontmatter 最少字段：

```yaml
---
id: note_20260618_a8f31c92
content_id: cnt_20260618_a8f31c92
title: Claude Code 的知识库工作流
source_type: url
source_uri: https://example.com/article
created_at: 2026-06-18T14:32:00+08:00
tags: [ai, knowledge-base, workflow]
stance: approve
summary: 一句话摘要
related_note_ids: []
topic_keys: []
status: active
---
```

`stance` 只允许：

- `approve`
- `doubt`
- `neutral`
- `todo`

正文固定五段：

1. 摘要
2. 关键信息
3. 我的判断
4. 可用场景
5. 主题候选

### 7.4 topic

文件命名：`wiki/topic-<topic_key>.md`

frontmatter 最少字段：

```yaml
---
id: topic_ai-knowledge-base
topic_key: ai-knowledge-base
title: AI 知识库
updated_at: 2026-06-17T18:40:00+08:00
source_note_ids:
  - note_20260618_a8f31c92
  - note_20260617_b7d42e10
tag_basis: [ai, knowledge-base]
status: active
---
```

正文固定五段：

1. 当前主题定义
2. 已形成的主要结论
3. 关键分歧/未决问题
4. 可延伸方向
5. 来源笔记列表

### 7.5 job state

文件命名：`state/jobs/<job_id>.json`

最少字段：

```json
{
  "job_id": "job_20260618143022_a8f31c92",
  "content_id": "cnt_20260618_a8f31c92",
  "input": {
    "source_type": "url",
    "source_uri": "https://example.com/article"
  },
  "status": "failed",
  "current_stage": "generation_requested",
  "completed_stages": [
    "received",
    "raw_saved"
  ],
  "failed_stage": "generation_requested",
  "error_message": "generation result not found",
  "retry_count": 1,
  "created_at": "2026-06-18T14:30:22+08:00",
  "updated_at": "2026-06-18T14:41:00+08:00"
}
```

## 8. 模块设计

### 8.1 `ingest`

职责：接收输入并驱动整条入库链路。

约束：

- 只负责 orchestration
- 不承载抓取、关联、编译细节
- 是唯一写路径总入口

### 8.2 `source_adapter`

职责：把不同来源统一为标准原文对象。

首版支持：

- URL adapter registry + generic fallback
- 文件类型：`txt / md / pdf`
- 直接文本

URL 路由策略：

- Phase 1 所有 URL 先走 `generic_web_adapter`
- GitHub 专用 adapter 放到 Phase 1.5 或 Phase 2
- 微信公众号首版降级为复制正文或文本导入

### 8.3 `note_builder`

职责：基于智能体生成结果生成单条原子笔记。

输入：

- 标准原文对象
- Prompt 模板
- 标签表
- `GenerationResult`

输出：

- `note.md`

首版不直接调用 LLM API。`note_builder` 负责生成请求、校验智能体结果、写入笔记，不自行生成摘要、标签、立场判断等语义结论。

### 8.4 `relation_builder`

职责：为新笔记建立轻量关联并推导主题归属。

首版规则：

- 标签重叠分
- 标题关键词重叠分
- AI 主题判断作为补充信号

满足两项以上才归入同一主题。

### 8.5 `topic_compiler`

职责：重建受影响的主题页。

规则：

- 只做主题页，不做实体页
- 至少 2 条相关笔记才允许创建主题页
- 每次只重建受影响主题页
- 不全量扫描重建

### 8.6 `index_builder`

职责：更新导航索引。

### 8.7 `ask_service`

职责：消费索引、主题页和笔记来回答问题。

约束：

- 只读
- 不更新主题页
- 不更新索引
- 不回写标签

### 8.8 `brief_service`

职责：生成选题和周报。

约束：

- 只读消费 `indexes/`、`wiki/`、`notes/`

## 9. 配置与 Prompt

### 9.1 配置

首版采用项目内配置文件 `kb.yaml`。

配置内容包括：

- 目录路径
- 标签表路径
- 主题规则
- 适配器开关
- 日志级别

首版不配置模型 provider，也不要求 API key。后续如果接入 Claude/OpenAI/本地模型，再增加 provider 配置，密钥仍走环境变量。

### 9.2 Prompt 管理

Prompt 文件化，存放在 `prompts/`。

至少包括：

- `note.md`
- `topic.md`
- `brief-topics.md`
- `brief-weekly.md`
- `tags.md`

Prompt 不写死在代码中。

## 10. 智能体生成策略

首版不实现 `llm_client`，不接 Claude/OpenAI/本地模型 API。

采用“生成请求 + 智能体生成 + 结构校验”方案。

执行方式：

1. `kb` 保存原文并创建 `GenerationRequest`
2. 智能体读取请求、原文和 Prompt
3. 智能体写入 `GenerationResult`
4. `kb` 使用 Pydantic 校验结果
5. 校验通过后写入 `notes/`、`wiki/`、`briefs/`

职责边界：

- `kb`：抓取、读取、落盘、生成请求、schema 校验、状态记录、索引更新
- 智能体：摘要、标签选择、立场判断、主题页编译、选题和周报文本生成

所有智能体生成结果必须采用结构化 schema。

支持类型：

- `note schema`
- `topic schema`
- `brief schema`

自由文本输出不允许直接落盘。

### 10.1 `GenerationRequest`

表示一次需要智能体完成的语义生成任务。

核心字段：

- `request_id`
- `job_id`
- `content_id`
- `generation_type`
- `source_paths`
- `prompt_path`
- `output_schema`
- `result_path`

文件格式：

- Markdown + YAML frontmatter
- frontmatter 存机器字段
- 正文写任务说明、读取范围、禁止事项、输出 schema

整体系统支持的 `generation_type` 包括：

- `note`
- `topic`
- `brief_topics`
- `brief_weekly`

Phase 1 只要求跑通 `note`，`topic / brief_topics / brief_weekly` 后续阶段实现。

GenerationRequest 示例：

```md
---
request_id: gen_20260618143022_a8f31c92_note
job_id: job_20260618143022_a8f31c92
content_id: cnt_20260618_a8f31c92
generation_type: note
source_paths:
  - raw/20260618/cnt_20260618_a8f31c92.md
prompt_path: prompts/note.md
output_schema: note_v1
result_path: state/generation_results/job_20260618143022_a8f31c92-note.yaml
---

## 任务

请读取 `source_paths` 中的原文，生成一份结构化 note 结果。

## 读取范围

- 必须读取 `source_paths`
- 可以读取 `prompt_path`
- 不要读取无关目录

## 输出要求

- 只写入 `result_path`
- 不要直接修改 `notes/`、`indexes/`、`wiki/`
- 输出必须符合 `note_v1` schema

## payload schema

见本文档 Phase 1 `generation_type: note` 的 `payload` schema。
```

### 10.2 `GenerationResult`

表示智能体生成后的结构化结果。

核心字段：

- `request_id`
- `job_id`
- `generation_type`
- `status`
- `payload`
- `sources`
- `created_at`

`payload` 必须通过对应 schema 校验后才能写入知识库。

Phase 1 `generation_type: note` 的 `payload` schema：

```yaml
payload:
  title: string
  summary: string
  tags: string[]          # 3-5 个
  stance: approve|doubt|neutral|todo
  key_points: string[]    # 3-7 条
  my_judgement: string
  useful_for: string[]
  related_topics: string[]
```

映射规则：

- `payload.title` -> note frontmatter `title`
- `payload.summary` -> note frontmatter `summary`
- `payload.tags` -> note frontmatter `tags`
- `payload.stance` -> note frontmatter `stance`
- `payload.related_topics` -> Phase 1 只作为正文“主题候选”，不创建 topic
- `topic_keys` Phase 1 默认空数组，Phase 2 由 topic compiler 写入

### 10.3 交接文件

建议首版增加：

- `state/generation_requests/`
- `state/generation_results/`

请求文件命名：

- `state/generation_requests/<job_id>-<generation_type>.md`

请求文件采用 Markdown + YAML frontmatter。frontmatter 存 `request_id / job_id / content_id / generation_type / source_paths / prompt_path / output_schema / result_path`，正文写任务说明、读取范围、禁止事项和输出 schema。

结果文件命名：

- `state/generation_results/<job_id>-<generation_type>.yaml`

`GenerationResult` YAML 最少字段：

```yaml
request_id: gen_20260618143022_a8f31c92_note
job_id: job_20260618143022_a8f31c92
content_id: cnt_20260618_a8f31c92
generation_type: note
status: completed
created_at: 2026-06-18T14:32:00+08:00
sources:
  - path: raw/20260618/cnt_20260618_a8f31c92.md
    source_uri: https://example.com/article
payload:
  title: 示例标题
  summary: 一句话摘要
  tags: [ai, writing]
  stance: approve
  key_points:
    - 关键点一
  my_judgement: 我的判断
  useful_for:
    - 写作选题
  related_topics: []
```

### 10.4 CLI 交接方式

`kb ingest <input>` 首次执行时完成：

1. 创建 job
2. 保存 raw
3. 创建 generation request
4. 返回 `needs_generation` 状态和请求文件路径

智能体生成结果后，再执行：

```bash
kb ingest --continue <job_id>
```

继续完成：

1. 读取 generation result
2. 校验 schema
3. 写入 note
4. Phase 1 更新 indexes
5. Phase 2 之后更新 relation/topic/index
6. 标记 job completed

Phase 1 先收窄为：

`ingest -> raw -> generation_request -> note -> indexes -> ask`

完整 topic 编译放到 Phase 2，`brief topics / brief weekly` 放到 Phase 3。

### 10.5 CLI 返回协议

所有 `kb` 命令默认向 stdout 输出 JSON。智能体负责把 JSON 转成自然语言回复。

通用字段：

- `ok`：布尔值
- `command`：实际执行的命令
- `status`：状态枚举
- `message`：面向智能体的简短说明

`status` 枚举：

- `needs_generation`
- `completed`
- `failed`
- `permanent_failed`
- `duplicate`

`next_action` 枚举：

- `write_generation_result`
- `run_continue`
- `retry`
- `none`

`kb ingest <input>` 返回示例：

```json
{
  "ok": true,
  "command": "kb ingest",
  "status": "needs_generation",
  "job_id": "job_20260618143022_a8f31c92",
  "content_id": "cnt_20260618_a8f31c92",
  "next_action": "write_generation_result",
  "generation_request_path": "state/generation_requests/job_20260618143022_a8f31c92-note.md",
  "generation_result_path": "state/generation_results/job_20260618143022_a8f31c92-note.yaml",
  "message": "Generation request created. Read request file and write result file."
}
```

`kb ingest --continue <job_id>` 成功返回示例：

```json
{
  "ok": true,
  "command": "kb ingest --continue",
  "status": "completed",
  "job_id": "job_20260618143022_a8f31c92",
  "note_path": "notes/20260618/note_20260618_a8f31c92.md",
  "index_paths": [
    "indexes/recent.md",
    "indexes/tags.md",
    "indexes/sources.md"
  ],
  "next_action": "none",
  "message": "Note persisted and indexes updated."
}
```

失败返回示例：

```json
{
  "ok": false,
  "command": "kb ingest --continue",
  "status": "failed",
  "job_id": "job_20260618143022_a8f31c92",
  "error_code": "GENERATION_RESULT_NOT_FOUND",
  "error_message": "Generation result file does not exist.",
  "retryable": true,
  "next_action": "write_generation_result"
}
```

## 11. 标签体系

采用“受控标签表 + AI 从中选择，必要时提新标签”。

规则：

- AI 每次选择 3-5 个标签
- 标签优先从现有标签表中选
- 没有合适标签时，只提候选，不自动入表

不允许首版使用完全自由标签模式。

## 12. 去重策略

采用双层去重：

1. `source_uri / 文件路径` 去重
2. `content_hash` 去重

不做语义去重。

重复入库命中时直接返回 `duplicate`，不重新生成 note。

返回示例：

```json
{
  "ok": true,
  "command": "kb ingest",
  "status": "duplicate",
  "existing_content_id": "cnt_20260618_a8f31c92",
  "existing_note_path": "notes/20260618/note_20260618_a8f31c92.md",
  "next_action": "none",
  "message": "Source already exists."
}
```

幂等要求：

- 同一 `content_id` 重复执行，不能生成重复内容
- `raw/` 已存在则不重复写
- `notes/` 内容未变化则不重复生成
- `wiki/` 按 `topic_key` 覆盖更新
- `indexes/` 每次重建当前视图，不追加脏数据

所有文件写入采用临时文件 + 原子替换：

```text
<target>.tmp -> rename -> <target>
```

中途失败时不得留下半截 Markdown/YAML 作为有效产物。

### 12.1 并发锁

Phase 1 同一时间只允许一个 `kb ingest`。

锁文件：

```text
state/locks/ingest.lock
```

如果锁存在，返回：

```json
{
  "ok": false,
  "command": "kb ingest",
  "status": "failed",
  "error_code": "INGEST_LOCKED",
  "error_message": "Another ingest job is running.",
  "retryable": true,
  "next_action": "retry"
}
```

## 13. Phase 1 错误码

Phase 1 只定义以下错误码：

- `INVALID_INPUT`
- `SOURCE_READ_FAILED`
- `RAW_SAVE_FAILED`
- `GENERATION_REQUEST_FAILED`
- `GENERATION_RESULT_NOT_FOUND`
- `GENERATION_RESULT_INVALID`
- `NOTE_WRITE_FAILED`
- `INDEX_UPDATE_FAILED`
- `INGEST_LOCKED`

`GenerationResult` schema 校验失败时：

- 不写入 `notes/`
- job 状态设为 `failed`
- `retryable: true`
- 返回 `GENERATION_RESULT_INVALID`
- 智能体修正 result YAML 后重新执行 `kb ingest --continue <job_id>`

## 14. Phase 1 配置

`kb.yaml` 最小字段：

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

Phase 1 输入范围：

- URL：`generic_web`
- 文件：`txt / md / pdf`
- 文本：直接文本

GitHub 专用 adapter 放到 Phase 1.5 或 Phase 2。微信公众号首版降级为复制正文或文本导入。

## 15. 主题页策略

### 15.1 `topic_key` 生成

规则：

- 全小写
- 英文或拼音短语
- 使用 `-` 连接
- 不带时间、不带版本号、不带情绪词

流程：

1. AI 给出 1-3 个候选主题
2. 与现有主题匹配
3. 命中则复用旧 `topic_key`
4. 没命中才创建新主题

### 15.2 新建条件

- 至少 2 条相关笔记才允许创建主题页
- 1 条笔记仅保留 `topic_keys` 候选，不建主题页

### 15.3 更新条件

只有两种情况更新主题页：

1. 新笔记命中已有 `topic_key`
2. 新笔记与已有笔记首次满足建主题条件

### 15.4 冲突处理

首版不自动合并主题，只做冲突标记，后续人工确认。

## 16. 索引设计

Phase 1 `indexes/` 只保留 3 类 Markdown 文件：

### 16.1 `recent.md`

包含：

- 最近新增笔记
- 最近更新索引时间

### 16.2 `tags.md`

包含：

- 标签名
- 对应 `note_ids`

### 16.3 `sources.md`

包含：

- 来源域名或来源类型
- 对应 `content_ids`
- 对应 `note_ids`

Phase 1 暂不生成：

- `indexes/topics.md`
- `indexes/*.json`
- 向量索引
- 数据库索引

Phase 2 引入：

- `indexes/topics.md`

索引只负责定位和裁剪候选集，不负责知识总结。

## 17. ask 路径

Phase 1 采用：

`扫描 notes -> 关键词匹配 -> 原子笔记回答`

执行步骤：

1. 扫描 `notes/**/*.md`
2. 读取 frontmatter：`title / tags / summary / source_uri / created_at`
3. 读取正文摘要段落
4. 用关键词匹配标题、标签、summary、来源和正文摘要
5. 选出 Top 3-5 条 note
6. 让智能体基于这些 note 生成回答
7. 回答必须附 note 文件路径和原始 source

Phase 2 采用：

`索引定位 -> 主题页优先 -> 原子笔记回退`

执行步骤：

1. 问题标准化：提取关键词、标签、时间限定、来源限定
2. 查 `topics.md`
3. 查 `tags.md`
4. 按需查 `recent.md` 和 `sources.md`
5. 优先读取命中的 1-3 个主题页
6. 必要时补读 2-5 条相关原子笔记
7. 输出答案并附来源

排序优先级：

1. 主题标题命中
2. 标签命中数量
3. 最近更新时间
4. 关联笔记数量

Phase 1 关键词命中打分：

- `title` 命中：+5
- `tags` 命中：+4
- `summary` 命中：+3
- 正文摘要命中：+2
- `source_uri` 命中：+1

同分时优先选择更新时间更新的 note。最终返回 Top 3-5 条 note 给智能体生成回答。

## 18. 错误处理与重试

### 18.1 原则

- 先保产物，再谈成功
- 失败必须可定位
- 重试只补失败阶段

### 18.2 状态机

- `received`
- `raw_saved`
- `note_generated`
- `relation_built`
- `topics_updated`
- `indexes_updated`
- `completed`
- `failed`
- `permanent_failed`

附加字段：

- `retryable: true/false`

### 18.3 错误分类

- 输入错误：直接 `permanent_failed`
- 抓取错误：允许重试，默认最多 3 次
- AI 处理错误：允许重试，保留已有产物
- 文件写入错误：失败，不回滚前序产物
- 主题页/索引更新错误：允许后续补跑

### 18.4 重试入口

- `kb retry job <job_id>`
- `kb retry content <content_id>`

### 18.5 降级策略

首版仅允许一种降级：

- 主题页更新失败时，保留 `raw/` 和 `notes/`，job 标记失败，后续补跑

## 19. CLI 设计

统一入口采用：

- `kb ingest`
- `kb ask`
- `kb brief`
- `kb retry`

未来可扩：

- `kb status`
- `kb rebuild`
- `kb doctor`

但这些不是首版必需。

### 19.1 智能体入口设计

`kb` CLI 是唯一执行内核，自然语言、slash 命令、skill 都只是智能体入口层。

推荐关系如下：

```text
用户自然语言或 slash/skill
  -> 智能体适配层
  -> kb CLI
  -> 文件型知识库
```

入口层必须保持轻量，只负责意图识别和命令映射，不允许直接读写 `raw/`、`notes/`、`wiki/`、`indexes/`，也不允许自行实现摘要、标签、关联、主题编译或索引更新逻辑。

首版以自然语言为默认入口，slash/skill 作为高频快捷入口。不同智能体可以采用不同的入口封装，但必须映射到同一组底层命令：

| 入口 | 底层命令 |
| --- | --- |
| 自然语言：把这个链接入库 | `kb ingest <input>` |
| 自然语言：查知识库里关于 xxx 的内容 | `kb ask "<question>"` |
| 自然语言：基于知识库给我选题 | `kb brief topics` |
| 自然语言：生成本周知识周报 | `kb brief weekly` |
| `/kb-ingest <input>` | `kb ingest <input>` |
| `/kb-ask <question>` | `kb ask "<question>"` |
| `/kb-brief-topics` | `kb brief topics` |
| `/kb-brief-weekly` | `kb brief weekly` |

当用户请求涉及知识库已有内容的查询、总结、选题或周报时，智能体必须调用 `kb`，不能凭当前上下文直接回答。命令返回结果需要适合智能体消费，至少包含成功状态、生成或命中的文件路径、摘要、来源引用、失败原因和下一步建议。

## 20. 代码组织建议

```text
kb/
  cli/
    main.py
    commands/
      ingest.py
      ask.py
      brief.py
      retry.py
  core/
    models/
      content.py
      note.py
      topic.py
      job.py
    pipeline/
      ingest_pipeline.py
    state/
      job_store.py
  adapters/
    registry.py
    url/
      generic_web.py
    file/
      text_file.py
      markdown_file.py
      pdf_file.py
    text/
      plain_text.py
  builders/
    note_builder.py
    relation_builder.py
    topic_compiler.py
    index_builder.py
    brief_builder.py
  services/
    ask_service.py
    brief_service.py
    generation_service.py
    prompt_loader.py
  storage/
    raw_store.py
    note_store.py
    topic_store.py
    index_store.py
  schemas/
    generation_schema.py
    note_schema.py
    topic_schema.py
    brief_schema.py
  config/
    loader.py
```

规则：

- `cli` 不直接读写知识文件
- `builder` 不直接改 `job state`
- `ask_service` 不触发写操作
- `github.py` 和 `wechat.py` 不进入 Phase 1 骨架，后续阶段再加入

## 21. 初始化与可观测性

### 21.1 `kb init`

首次运行可用 `kb init` 创建目录和默认文件：

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

`kb init` 是初始化辅助命令，不改变 Phase 1 主链路。

### 21.2 可观测性

首版保留 3 个观察面：

1. `job state`
2. `logs/`
3. 后续预留 `kb status`

日志建议至少分：

- `ingest.log`
- `ask.log`

重点记录：

- 输入来源
- adapter 命中结果
- AI 调用耗时
- schema 校验失败
- topic/index 更新结果

Phase 1 日志只记录路径、状态、错误码、耗时，不记录完整原文，不记录密钥、token、密码。

## 22. 验证边界

首版至少覆盖 4 类测试：

1. adapter 测试
2. schema 测试
3. pipeline 测试
4. query 测试

验证重点不是模型是否“聪明”，而是：

- 链路是否稳定
- 状态是否可信
- 结果是否可追溯

## 23. 演进边界

首版之后允许的扩展方向：

- 新增 URL adapter
- 扩展文件类型
- 增加新的 brief 类型
- 增加新的索引视图
- 从智能体生成扩到 API provider

这些扩展不应改变主链：

`content -> note -> relation -> topic -> index -> ask/brief`

## 24. 结论

这套架构本质上是一个本地知识编译器，而不是一个泛化知识平台。

它的核心约束已经明确：

- 写路径唯一
- 读路径只读
- 内容与状态分离
- AI 输出结构化
- 主题页是主要知识出口

在 MVP 阶段，这套架构足够稳、足够轻，也保留了后续扩展余地。
