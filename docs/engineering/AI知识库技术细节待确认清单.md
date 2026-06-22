# AI 知识库技术细节待确认清单

## 1. 文档目的

本文档用于整理 AI 知识库 MVP 的技术实现细节，作为后续实施计划和开发排期前的确认清单。

路径基准：本文中的 `raw/`、`notes/`、`wiki/`、`briefs/`、`indexes/`、`prompts/`、`state/` 均指 `knowledge/` 工作区下的相对路径；功能代码位于 `knowledge/kb/`。

文档分为三类内容：

- 已确认：前面讨论已收敛的技术决策
- 建议确认：我建议尽快拍板的实现细节
- 暂缓处理：不影响 MVP 第一阶段落地，可以延后决定的点

---

## 2. 已确认的技术决策

### 2.1 产品运行形态

- 本地运行
- CLI 工具形态
- 统一命令入口：`kb <subcommand>`
- 单进程、串行执行

### 2.2 存储与执行模型

- 纯文件存储
- 全同步 `ingest`
- 分阶段落盘
- 状态标记
- 支持重试

### 2.3 知识组织方式

- 只做主题页，不做实体页
- 主题页只更新受影响主题，不全量重建
- `ask` 路径：索引定位 -> 主题页优先 -> 原子笔记回退
- 主题页不是索引，索引只做导航

### 2.4 输入范围

- URL 链接
- 本地文件：`txt / md / pdf`

### 2.5 关联与归类

- 关联方式：标签重叠 + 标题关键词打分
- 主题归类：规则信号为主，AI 作为补充信号
- 标签体系：受控标签表 + AI 选择，必要时提新标签

### 2.6 智能体生成与 Prompt

- 首版不接 LLM API provider
- 语义生成由当前智能体完成
- `kb` 只负责生成请求、校验结构、落盘和更新索引
- Prompt 文件化管理
- 智能体输出必须结构化，并通过 schema 校验

### 2.7 去重与幂等

- 双层去重：`source_uri/文件路径` + `content_hash`
- 幂等要求明确，不能因重试生成重复内容

### 2.8 ID 与文件命名

- ID 采用“日期 + 短 hash”，不使用自增序号
- `content_id`：`cnt_<YYYYMMDD>_<source_key_hash>`
- `note_id`：`note_<YYYYMMDD>_<source_key_hash>`
- `job_id`：`job_<YYYYMMDDHHMMSS>_<source_key_hash>`
- `request_id`：`gen_<YYYYMMDDHHMMSS>_<source_key_hash>_<generation_type>`
- `source_key_hash` 来源：URL 用标准化 `source_uri`，本地文件用绝对路径 + 文件内容 hash，纯文本用文本内容 hash

### 2.9 Phase 1 note schema

- `GenerationResult.payload` 必须包含 `title / summary / tags / stance / key_points / my_judgement / useful_for / related_topics`
- `tags` 控制在 3-5 个
- `key_points` 控制在 3-7 条
- `stance` 只允许 `approve / doubt / neutral / todo`
- `related_topics` 只作为主题候选，Phase 1 不创建 topic
- `topic_keys` Phase 1 默认空数组，Phase 2 由 topic compiler 写入

### 2.10 GenerationRequest 交接协议

- `GenerationRequest` 使用 Markdown + YAML frontmatter
- 文件路径：`state/generation_requests/<job_id>-<generation_type>.md`
- frontmatter 存 `request_id / job_id / content_id / generation_type / source_paths / prompt_path / output_schema / result_path`
- 正文写任务说明、读取范围、禁止事项和输出 schema
- 智能体只能写入 `result_path`
- 智能体不能直接修改 `notes/`、`indexes/`、`wiki/`
- `GenerationResult` 使用 YAML，供 `kb` 做 Pydantic schema 校验

### 2.11 CLI 返回协议

- 所有 `kb` 命令默认向 stdout 输出 JSON
- 智能体负责把 JSON 转成自然语言回复
- 通用字段：`ok / command / status / message`
- `status` 枚举：`needs_generation / completed / failed / permanent_failed / duplicate`
- `next_action` 枚举：`write_generation_result / run_continue / retry / none`
- 失败结果必须包含 `error_code / error_message / retryable / next_action`

### 2.12 Phase 1 工程运行细节

- 文件写入采用临时文件 + 原子替换：`*.tmp -> rename`
- 同一时间只允许一个 `kb ingest`，锁文件为 `state/locks/ingest.lock`
- 重复入库命中 `source_uri` 或 `content_hash` 时返回 `duplicate`，不重新生成 note
- Phase 1 错误码限定为：`INVALID_INPUT / SOURCE_READ_FAILED / RAW_SAVE_FAILED / GENERATION_REQUEST_FAILED / GENERATION_RESULT_NOT_FOUND / GENERATION_RESULT_INVALID / NOTE_WRITE_FAILED / INDEX_UPDATE_FAILED / INGEST_LOCKED`
- `kb.yaml` 保留最小配置：`paths / phase / ingest / ask`
- Phase 1 输入范围：`generic_web URL / txt / md / pdf / 直接文本`
- GitHub 专用 adapter 放到 Phase 1.5 或 Phase 2，微信公众号降级为复制正文或文本导入
- `ask` 使用关键词打分：`title +5 / tags +4 / summary +3 / 正文摘要 +2 / source_uri +1`，同分按更新时间优先
- Phase 1 日志只保留 `logs/ingest.log` 和 `logs/ask.log`
- 日志只记录路径、状态、错误码、耗时，不记录完整原文，不记录密钥
- `GenerationResult` schema 校验失败时不写入 `notes/`，job 标记 `failed`，`retryable: true`，返回 `GENERATION_RESULT_INVALID`
- `kb init` 只作为初始化辅助命令，创建目录和默认文件，不改变 Phase 1 主链路

---

## 3. 建议采用的技术方案

以下是我建议的首版技术选型，默认作为推荐方案，后续只需要确认是否接受。

### 3.1 语言与工程基础

- Python 3.12
- `uv` 管理依赖
- `pytest` 做测试
- `ruff` 做 lint 和格式检查

### 3.2 CLI 层

- `Typer`

原因：

- 适合 `kb ingest / kb ask / kb brief / kb retry` 这种子命令结构
- 参数声明清晰
- 文档和生态成熟

### 3.3 数据与 schema

- `Pydantic`

用途：

- `Content`
- `Note`
- `Topic`
- `Job`
- `GenerationRequest`
- `GenerationResult`
- 智能体生成结果 schema 校验

### 3.4 文件读写

- `python-frontmatter`：Markdown + YAML frontmatter
- 标准库 `pathlib`：路径管理
- 标准库 `json` / `yaml`：状态和元数据文件

### 3.5 URL 抓取

- `httpx`：HTTP 请求
- `trafilatura`：通用网页正文抽取

建议策略：

- `generic_web_adapter` 用 `httpx + trafilatura`
- Phase 1 不做 `github_adapter` 和 `wechat_adapter`
- GitHub 专用 adapter 放到 Phase 1.5 或 Phase 2
- 微信公众号首版降级为复制正文或文本导入

### 3.6 本地文件解析

- `txt/md`：标准文本读取
- `PyMuPDF`：PDF 文本提取

### 3.7 日志与状态

- 标准库 `logging`
- `state/jobs/*.json` 保存任务状态

### 3.8 智能体生成层

- 首版不实现 `llm_client`
- 不接 Claude/OpenAI/本地模型 API
- 项目内统一 `generation_request / generation_result`
- 通过 `prompts/*.md` 加载 Prompt
- 智能体读取请求和原文后生成结构化结果
- `kb` 校验结果后再写入 `notes/`、`wiki/`、`briefs/`

首版职责边界：

- `kb`：抓取、读取、落盘、生成请求、schema 校验、状态记录、索引更新
- 智能体：摘要、标签选择、立场判断、主题页编译、选题和周报文本生成

---

## 4. 建议优先确认的技术问题

这些问题会直接影响开发顺序，最好在实施计划前拍板。

### 4.1 Python 包管理工具

候选：

- `uv`（推荐）
- `poetry`
- `pip + requirements.txt`

我的建议：

- 选 `uv`

原因：

- 速度快
- 配置简单
- 适合这种本地 CLI 工具项目

### 4.2 配置文件格式

候选：

- `kb.yaml`（推荐）
- `kb.toml`
- `config.json`

我的建议：

- 选 `kb.yaml`

原因：

- 可读性最好
- 适合目录、标签表、主题规则、适配器开关这种配置结构

### 4.3 语义生成方式

候选：

- 智能体生成（推荐，已确认）
- Claude/OpenAI API
- 本地模型 API

已确认：

- 首版采用智能体生成
- 暂不接任何 LLM API provider

原因：

- 不需要 API key 和 provider 配置
- 更符合通过 Codex、Claude Code 使用知识库的目标
- 先把 `generation_request -> generation_result -> schema 校验 -> 落盘` 链路跑通
- 后续要自动化时，再把智能体生成层替换为 API provider

### 4.4 微信公众号策略

候选：

- 接外部 reader 服务
- 做单独适配器
- 首版暂时降级为“先复制正文再导入”

我的建议：

- 不要首版硬啃反爬
- 如果没有稳定现成方案，先降级处理

### 4.5 GitHub 链接处理策略

候选：

- 先走通用网页解析
- 做 GitHub 专用 adapter
- 直接接 GitHub API

我的建议：

- Phase 1 先走 `generic_web_adapter`
- GitHub 专用 adapter 放到 Phase 1.5 或 Phase 2
- 不把 OAuth/API 认证引进首版

---

## 5. 建议的代码实现拆分

### 5.1 第一层：工程骨架

- CLI 入口
- 配置加载
- 基础目录初始化
- 日志初始化

### 5.2 第二层：存储与状态

- `raw_store`
- `note_store`
- `topic_store`
- `index_store`
- `job_store`

### 5.3 第三层：输入适配器

- `generic_web_adapter`
- `text_file_adapter`
- `markdown_file_adapter`
- `pdf_file_adapter`

### 5.4 第四层：知识生成

- `note_builder`
- `relation_builder`
- `topic_compiler`
- `index_builder`

### 5.5 第五层：消费能力

- `ask_service`
- `brief_service`
- `retry_service`

---

## 6. 建议的开发优先级

### Phase 1：最小可用知识库

- 工程骨架
- 配置系统
- 存储层
- job state
- 文件和通用网页输入
- raw 落盘
- `generation_request / generation_result`
- note 生成与 schema 校验
- Markdown indexes：`recent.md / tags.md / sources.md`
- ask：扫描 `notes/**/*.md` 后做关键词匹配

目标链路：

`ingest -> raw -> generation_request -> note -> indexes -> ask`

### Phase 2：知识编译能力

- relation
- topic
- topic-first ask

### Phase 3：知识反向产出

- brief topics
- brief weekly
- retry

---

## 7. 当前不建议首版处理的技术点

这些点不是不能做，而是现在做收益太低。

- 向量检索
- 数据库
- Web 前端
- 多用户权限
- 多 provider 路由
- 自动订阅与后台定时任务
- 音视频识别
- docx / epub / html 等更多文件格式
- 自动主题合并

---

## 8. 待确认事项清单

下面这部分适合你逐条确认，后续我可以直接把确认结果转成实施计划。

### A. 工程与依赖

- [x] Python 版本是否定为 `3.12`
- [x] 依赖管理是否定为 `uv`
- [x] 测试框架是否定为 `pytest`
- [x] 代码规范是否定为 `ruff`

### B. 配置与运行

- [x] 配置文件是否定为 `kb.yaml`
- [x] 密钥是否全部走环境变量
- [x] CLI 是否只保留 `kb ingest / ask / brief / retry`

### C. 输入适配器

- [x] 首版是否只实现 `generic_web + txt + md + pdf + text`
- [x] 微信公众号是否延后为降级方案

### D. 智能体生成与 Prompt

- [x] 首版是否不接 LLM API provider
- [x] 语义生成是否由当前智能体完成
- [x] Prompt 是否全部文件化
- [x] 智能体生成结果是否全部走 Pydantic schema 校验

### E. 知识层

- [x] 是否只做主题页
- [x] 是否坚持“2 条笔记以上才建主题页”
- [x] 是否坚持索引不承载结论

### F. 交付范围

- [x] 第一阶段是否只要求跑通 `ingest -> note -> indexes -> ask`
- [x] 完整 topic 编译是否放到第二阶段
- [x] `brief` 是否放到第三阶段

---

## 9. 我对当前方案的判断

当前最合理的策略不是继续扩需求，而是尽快把这些待确认项压实。只要上面这份清单确认完成，后续就可以直接生成实施计划，并按阶段进入开发。

一句话总结：

> 先把工程底盘、输入适配、note/indexes/ask 这条主链做稳，topic 编译和 brief 往后排。
