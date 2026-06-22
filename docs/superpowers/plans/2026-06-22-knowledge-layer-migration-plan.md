# Knowledge Layer Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前仓库拆成“外层项目开发壳 + 内层知识库本体”，其中 `knowledge/` 同时包含知识库功能代码、知识库配置、知识库数据和智能体使用规则。

**Architecture:** 外层只保留开发这个知识库项目所需的工程配置、测试、产品/工程文档；内层 `knowledge/` 是实际知识库工作区，包含 `kb/` 功能代码和 `raw/ notes/ wiki/ briefs/ indexes/ prompts/ state/ logs/` 等运行目录。日常使用 Claude Code/Codex 时进入 `knowledge/`，智能体可以直接访问本目录下的 `kb/`，不需要跨目录调用外层源码。

**Tech Stack:** Python 3.12+、Typer、Pydantic、Hatchling、uv、pytest、ruff、Markdown/YAML 文件存储。

---

## 目标结构

```text
fuxix/
  AGENTS.md
  README.md
  pyproject.toml
  uv.lock
  tests/
  docs/
    product/
    engineering/
    superpowers/

  knowledge/
    AGENTS.md
    kb.yaml
    kb/
    docs/
      智能体使用协议.md
    prompts/
    raw/
    notes/
    wiki/
    briefs/
    indexes/
    state/
    logs/
```

## 职责边界

### 外层：项目开发

外层是开发知识库系统的工程目录。

保留：

- `pyproject.toml`
- `uv.lock`
- `tests/`
- `docs/product/`
- `docs/engineering/`
- `docs/superpowers/`
- 根目录 `AGENTS.md`

外层规则：

- 改 `knowledge/kb/` 功能代码时，仍然在外层运行 `uv run pytest -q` 和 `uv run ruff check .`。
- 外层 `docs/` 不放智能体使用协议，只放产品设计、工程架构、实施计划。
- 外层不再直接存放 `raw/ notes/ indexes/ state/ prompts/ kb.yaml`。

### 内层：知识库本体

内层 `knowledge/` 是真实个人知识库工作区。

保留：

- `knowledge/kb/`：知识库功能代码
- `knowledge/kb.yaml`：知识库配置
- `knowledge/prompts/`：生成 prompt
- `knowledge/raw/`：原始资料
- `knowledge/notes/`：原子笔记
- `knowledge/wiki/`：主题页
- `knowledge/briefs/`：选题和周报
- `knowledge/indexes/`：索引
- `knowledge/state/`：任务状态、生成请求和结果
- `knowledge/logs/`：运行日志
- `knowledge/docs/`：Claude Code/Codex 使用协议
- `knowledge/AGENTS.md`：知识库使用规则

内层规则：

- 在 `knowledge/` 使用知识库时，当前目录就是知识库根目录。
- 入库、查询、主题编译、选题、周报通过本目录下的 `kb` 功能代码对应 CLI 执行。
- 不要直接手改 `raw/ notes/ wiki/ briefs/ indexes/ state/`，除非用户明确要求修复数据。
- 修改 `knowledge/kb/` 属于功能开发，不属于普通知识库使用。

## 当前文件迁移表

| 当前路径 | 目标路径 | 说明 |
| --- | --- | --- |
| `kb/` | `knowledge/kb/` | 知识库功能代码整体迁入内层 |
| `kb.yaml` | `knowledge/kb.yaml` | 知识库实例配置 |
| `raw/` | `knowledge/raw/` | 原始资料 |
| `notes/` | `knowledge/notes/` | 原子笔记 |
| `wiki/` | `knowledge/wiki/` | 主题页；当前可能不存在，迁移时创建 |
| `briefs/` | `knowledge/briefs/` | 选题/周报；当前可能不存在，迁移时创建 |
| `indexes/` | `knowledge/indexes/` | 索引 |
| `prompts/` | `knowledge/prompts/` | 实例 prompt |
| `state/` | `knowledge/state/` | job、generation request/result |
| `logs/` | `knowledge/logs/` | 当前可能不存在，迁移时创建 |
| `docs/AI知识库MVP产品设计.md` | `docs/product/AI知识库MVP产品设计.md` | 外层产品文档 |
| `docs/AI知识库技术架构文档.md` | `docs/engineering/AI知识库技术架构文档.md` | 外层工程文档 |
| `docs/AI知识库技术细节待确认清单.md` | `docs/engineering/AI知识库技术细节待确认清单.md` | 外层工程文档 |
| `docs/superpowers/*` | `docs/superpowers/*` | 保持原位，仍是开发过程文档 |
| 根目录 `07/08/09-*.md` | 保留根目录 | 用户确认暂不迁移 |
| `task_plan.md`、`findings.md`、`progress.md` | `docs/superpowers/archive/` | 旧 planning 记录，实施前确认是否迁移 |

## 关键技术改动

### `pyproject.toml`

迁移后包目录不再是根目录 `kb/`，而是 `knowledge/kb/`。

需要调整：

```toml
[project.scripts]
kb = "kb.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["knowledge/kb"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["knowledge"]
```

保留命令入口 `kb = "kb.cli.main:app"`，因为 Python 包名仍然是 `kb`，只是源码物理位置变成 `knowledge/kb`。

### 测试

测试仍放在外层 `tests/`。

迁移后测试应满足：

- `from kb.cli.main import app` 仍然可用。
- `uv run pytest -q` 在仓库根目录通过。
- 测试中的临时 workspace 仍然只模拟知识库运行根，不依赖真实 `knowledge/` 数据。

### CLI 当前工作目录规则

暂不引入 `--root`。

规则保持简单：

- 在外层跑测试：测试通过 `monkeypatch.chdir(workspace)` 显式切换临时知识库根。
- 在内层使用知识库：用户/智能体进入 `knowledge/` 后执行 `kb ...`。
- CLI 内部继续使用 `Path.cwd()` 作为知识库根目录。

## 实施任务

### Task 1: 建立外层/内层规则文档

**Files:**

- Modify: `AGENTS.md`
- Create: `knowledge/AGENTS.md`
- Create: `knowledge/docs/智能体使用协议.md`

- [ ] **Step 1: 修改根目录 AGENTS.md**

将根目录规则改成只描述“开发知识库项目”的规则：

```md
# 项目开发规则

## 目标

本仓库用于开发个人 AI 知识库系统。仓库外层是工程项目，`knowledge/` 是实际知识库工作区。

## 目录边界

- `knowledge/kb/`：知识库功能代码
- `tests/`：功能代码测试
- `docs/product/`：产品文档
- `docs/engineering/`：工程文档
- `docs/superpowers/`：实施计划和过程文档
- `knowledge/`：个人知识库本体，包含代码、配置、数据和使用规则

## 开发规则

- 修改功能代码后运行 `uv run pytest -q` 和 `uv run ruff check .`
- 普通知识库使用请求进入 `knowledge/` 规则处理
- 不把 `knowledge/raw/ notes/ wiki/ briefs/ indexes/ state/` 当作项目源码修改
- 删除文件、回滚、密钥、环境变量、数据库变更、发布类动作必须先确认
```

- [ ] **Step 2: 创建 knowledge/AGENTS.md**

```md
# 知识库使用规则

## 目标

本目录是个人知识库工作区。这里包含知识库功能代码、配置、数据和智能体使用协议。

## 目录边界

- `kb/`：知识库功能代码。只有用户要求改功能、修 bug、跑测试时才修改。
- `kb.yaml`：知识库配置。
- `prompts/`：生成 note/topic/brief 使用的 prompt。
- `raw/`：原始资料。
- `notes/`：原子笔记。
- `wiki/`：主题页。
- `briefs/`：选题和周报。
- `indexes/`：索引。
- `state/`：job、generation request/result。
- `docs/`：智能体使用协议和知识库操作说明。

## 使用规则

- 入库使用 `kb ingest <input>`。
- 查询使用 `kb ask "<question>"`。
- 主题编译继续执行使用 `kb compile --continue <job_id> --topic-key <topic_key>`。
- 生成选题使用 `kb brief topics`。
- 生成周报使用 `kb brief weekly`。
- 遇到 `needs_generation` 时，智能体读取 generation request，写入 generation result，再执行对应 `--continue`。
- 不直接手改 `raw/ notes/ wiki/ briefs/ indexes/ state/`，除非用户明确要求修复数据。
```

- [ ] **Step 3: 创建 knowledge/docs/智能体使用协议.md**

```md
# 智能体使用协议

## 意图映射

| 用户意图 | 命令 |
| --- | --- |
| 保存链接、文件、文本、想法 | `kb ingest <input>` |
| 查询知识库已有内容 | `kb ask "<question>"` |
| 继续主题页编译 | `kb compile --continue <job_id> --topic-key <topic_key>` |
| 生成可写选题 | `kb brief topics` |
| 生成知识周报 | `kb brief weekly` |

## 两段式生成流程

1. 执行命令，得到 `needs_generation`。
2. 读取返回的 `generation_request_path`。
3. 按请求读取来源文件和 prompt。
4. 写入 `generation_result_path`。
5. 执行对应 `--continue` 命令。

## 回复规则

- 回复用户时说明实际执行的 `kb` 命令。
- 查询或生成内容时必须附来源文件或来源链接。
- 失败时只返回命令给出的错误码、错误信息和下一步动作，不编造结果。
```

- [ ] **Step 4: 验证文档存在**

Run:

```powershell
Test-Path knowledge\AGENTS.md; Test-Path knowledge\docs\智能体使用协议.md
```

Expected:

```text
True
True
```

### Task 2: 迁移 `kb/` 功能代码到 `knowledge/kb/`

**Files:**

- Move: `kb/` -> `knowledge/kb/`
- Modify: `pyproject.toml`

- [ ] **Step 1: 移动代码目录**

Run:

```powershell
New-Item -ItemType Directory -Force knowledge | Out-Null
git mv kb knowledge\kb
```

Expected:

```text
knowledge/kb/cli/main.py exists
kb/ no longer exists
```

- [ ] **Step 2: 更新 pyproject.toml**

将构建配置改成：

```toml
[tool.hatch.build.targets.wheel]
packages = ["knowledge/kb"]
```

将 pytest 配置改成：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["knowledge"]
```

- [ ] **Step 3: 验证 import**

Run:

```powershell
uv run python -c "import kb; print(kb.__file__)"
```

Expected:

```text
...\knowledge\kb\__init__.py
```

### Task 3: 迁移知识库运行目录到 `knowledge/`

**Files:**

- Move: `kb.yaml` -> `knowledge/kb.yaml`
- Move: `raw/` -> `knowledge/raw/`
- Move: `notes/` -> `knowledge/notes/`
- Move: `indexes/` -> `knowledge/indexes/`
- Move: `prompts/` -> `knowledge/prompts/`
- Move: `state/` -> `knowledge/state/`
- Create if missing: `knowledge/wiki/`
- Create if missing: `knowledge/briefs/`
- Create if missing: `knowledge/logs/`

- [ ] **Step 1: 移动已有运行目录**

Run:

```powershell
git mv kb.yaml knowledge\kb.yaml
git mv raw knowledge\raw
git mv notes knowledge\notes
git mv indexes knowledge\indexes
git mv prompts knowledge\prompts
git mv state knowledge\state
```

Expected:

```text
knowledge/kb.yaml exists
knowledge/raw exists
knowledge/notes exists
knowledge/indexes exists
knowledge/prompts exists
knowledge/state exists
```

- [ ] **Step 2: 创建缺失运行目录**

Run:

```powershell
New-Item -ItemType Directory -Force knowledge\wiki, knowledge\briefs, knowledge\logs | Out-Null
```

Expected:

```text
knowledge/wiki exists
knowledge/briefs exists
knowledge/logs exists
```

- [ ] **Step 3: 从 `knowledge/` 运行一次只读查询 smoke test**

Run:

```powershell
Push-Location knowledge
uv run kb ask "AI"
Pop-Location
```

Expected:

```json
{"ok":true,"command":"kb ask",...}
```

### Task 4: 整理外层 docs 目录

**Files:**

- Create: `docs/product/`
- Create: `docs/engineering/`
- Move: `docs/AI知识库MVP产品设计.md` -> `docs/product/AI知识库MVP产品设计.md`
- Move: `docs/AI知识库技术架构文档.md` -> `docs/engineering/AI知识库技术架构文档.md`
- Move: `docs/AI知识库技术细节待确认清单.md` -> `docs/engineering/AI知识库技术细节待确认清单.md`

- [ ] **Step 1: 创建文档分层目录**

Run:

```powershell
New-Item -ItemType Directory -Force docs\product, docs\engineering | Out-Null
```

- [ ] **Step 2: 移动产品和工程文档**

Run:

```powershell
git mv docs\AI知识库MVP产品设计.md docs\product\AI知识库MVP产品设计.md
git mv docs\AI知识库技术架构文档.md docs\engineering\AI知识库技术架构文档.md
git mv docs\AI知识库技术细节待确认清单.md docs\engineering\AI知识库技术细节待确认清单.md
```

- [ ] **Step 3: 检查外层 docs 不包含 agent 协议**

Run:

```powershell
rg -n "Codex|Claude Code|智能体使用协议|kb ingest|kb ask" docs
```

Expected:

外层工程文档可以保留底层 CLI 协议，但不应出现面向 Codex/Claude Code 的操作协议。如果仍有大段智能体使用说明，迁入 `knowledge/docs/智能体使用协议.md`。

### Task 5: 处理旧 planning 文件

**Files:**

- Move candidate: `task_plan.md`
- Move candidate: `findings.md`
- Move candidate: `progress.md`

- [ ] **Step 1: 保留三份 AI 思考源材料**

用户确认 `07-ai-product-thinking-20260604.md`、`08-ai-architecture-thinking-20260610.md`、`09-ai-tech-thinking-20260609.md` 暂时继续放在外层根目录，不迁入 `knowledge/`。

- [ ] **Step 2: 处理旧 planning 文件**

推荐迁移到：

```text
docs/superpowers/archive/
```

Run:

```powershell
New-Item -ItemType Directory -Force docs\superpowers\archive | Out-Null
git mv task_plan.md docs\superpowers\archive\task_plan.md
git mv findings.md docs\superpowers\archive\findings.md
git mv progress.md docs\superpowers\archive\progress.md
```

### Task 6: 更新测试以适配 `knowledge/kb`

**Files:**

- Modify: `tests/*.py` only if needed
- Modify: `pyproject.toml`

- [ ] **Step 1: 跑测试确认迁移后失败点**

Run:

```powershell
uv run pytest -q
```

Expected:

如果 `pythonpath = ["knowledge"]` 配置正确，应直接通过或只出现路径断言失败。

- [ ] **Step 2: 修复路径断言**

重点检查这些断言：

```python
assert (workspace / "state" / "generation_requests").exists()
assert (workspace / "notes").glob("**/*.md")
assert data["topic_request_paths"] == [...]
```

这些测试使用临时 workspace，不应改成真实 `knowledge/` 路径。

- [ ] **Step 3: 验证全量测试**

Run:

```powershell
uv run pytest -q
```

Expected:

```text
29 passed
```

### Task 7: 更新文档引用

**Files:**

- Modify: `docs/product/AI知识库MVP产品设计.md`
- Modify: `docs/engineering/AI知识库技术架构文档.md`
- Modify: `docs/engineering/AI知识库技术细节待确认清单.md`
- Modify: `knowledge/docs/智能体使用协议.md`

- [ ] **Step 1: 全局查找旧目录引用**

Run:

```powershell
rg -n "raw/|notes/|wiki/|briefs/|indexes/|prompts/|state/|kb/" docs knowledge\docs AGENTS.md knowledge\AGENTS.md
```

- [ ] **Step 2: 更新语义，而不是机械替换**

规则：

- 工程文档描述系统内部目录时，可以继续写 `raw/ notes/ ...`，但要明确这些路径相对于 `knowledge/`。
- 外层项目文档描述源码时，应写 `knowledge/kb/`。
- 智能体使用协议写命令时，不需要加 `knowledge/` 前缀，因为执行目录就是 `knowledge/`。

- [ ] **Step 3: 验证文档无旧边界误导**

Run:

```powershell
rg -n "根目录.*raw|根目录.*notes|外层.*raw|外层.*state|docs/agent|agent/" AGENTS.md docs knowledge
```

Expected:

不应再出现“外层根目录直接作为知识库运行目录”的描述。

### Task 8: 最终验证和提交

**Files:**

- All migrated files

- [ ] **Step 1: 运行全量测试**

Run:

```powershell
uv run pytest -q
```

Expected:

```text
29 passed
```

- [ ] **Step 2: 运行静态检查**

Run:

```powershell
uv run ruff check .
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: 检查工作区结构**

Run:

```powershell
Get-ChildItem -Name
Get-ChildItem -Name knowledge
```

Expected root:

```text
AGENTS.md
README.md
pyproject.toml
uv.lock
tests
docs
knowledge
```

Expected knowledge:

```text
AGENTS.md
kb.yaml
kb
docs
prompts
raw
notes
wiki
briefs
indexes
state
logs
```

- [ ] **Step 4: 检查根目录不再混入知识库运行目录**

Run:

```powershell
Test-Path raw; Test-Path notes; Test-Path indexes; Test-Path prompts; Test-Path state; Test-Path kb.yaml
```

Expected:

```text
False
False
False
False
False
False
```

- [ ] **Step 5: 提交**

Run:

```powershell
git add .
git commit -m "chore: separate project shell and knowledge workspace"
```

## 风险与应对

- **风险：`kb` 包移动后测试无法 import。**  
  应对：在 `pyproject.toml` 增加 `pythonpath = ["knowledge"]`，并将 Hatch package 指向 `knowledge/kb`。

- **风险：日常在 `knowledge/` 执行 `kb` 时找不到命令。**  
  应对：使用 `uv run kb ...` 或在外层安装 editable 包。后续如果需要更顺手，再单独设计 `knowledge/scripts/kb.ps1`，本次不加入。

- **风险：文档路径大量变化导致引用失效。**  
  应对：迁移后用 `rg` 查旧路径和旧边界描述，只修正与本次分层直接相关的引用。

- **风险：移动目录被误认为删除。**  
  应对：实施时使用 `git mv`，并在提交前用 `git status --short` 检查 rename 是否清晰。

## 实施前确认点

1. 三份根目录源材料 `07/08/09-*.md` 暂时保留在外层。
2. 旧 planning 文件 `task_plan.md / findings.md / progress.md` 迁到 `docs/superpowers/archive/`。
3. 日常使用命令先用 `uv run kb ...`，后续再考虑快捷 wrapper。
