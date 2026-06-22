# 项目开发规则

## 目标

本仓库用于开发个人 AI 知识库系统。仓库外层是工程项目，`knowledge/` 是实际知识库工作区。

## 工作原则

- 默认中文沟通，代码、命令、文件名保留英文
- 先定规则，再做内容
- 只改用户明确要求的内容，不额外扩展
- 复杂任务先写计划，再执行
- 修改后主动自检

## 目录边界

- `knowledge/kb/`：知识库功能代码
- `tests/`：功能代码测试
- `docs/product/`：产品文档
- `docs/engineering/`：工程文档
- `docs/superpowers/`：实施计划和过程文档
- `knowledge/`：个人知识库本体，包含代码、配置、数据和使用规则
- 根目录：保留工程配置、总规则、少量源材料和项目总览文件

## 开发规则

- 修改功能代码后运行 `uv run pytest -q` 和 `uv run ruff check .`
- 普通知识库使用请求进入 `knowledge/` 规则处理
- 不把 `knowledge/raw/`、`knowledge/notes/`、`knowledge/wiki/`、`knowledge/briefs/`、`knowledge/indexes/`、`knowledge/state/` 当作项目源码修改
- 外层 `docs/` 不放智能体使用协议；相关协议放在 `knowledge/docs/`

## 交付要求

- 新增文档要命名清晰，优先使用简短中文名
- 产品/方案类文档必须包含：目标、范围、流程、数据、技术选型、验收
- 不写空话，不写大而全，不留 TODO

## 变更约束

- 删除文件、回滚、密钥、环境变量、数据库变更、发布类动作，先问用户
- 任何修改都要能追溯到当前请求
