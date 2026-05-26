---
name: 数据库可移植性与密钥卫生
description: 在同时支持 SQLite（本地）与 MySQL（生产）的前提下，审查 ORM/原始 SQL 与配置是否引入不可移植或易泄露密钥的写法。
---

# 数据库可移植性与密钥卫生

## Context

项目定案为生产 **MySQL**、本地可选 **SQLite**（见 [AGENTS.md](AGENTS.md)、[技术选型与约定.md](技术选型与约定.md)、[backend/app/config.py](backend/app/config.py) 类配置）。类型检查器不会阻止 `text("ONLY MYSQL ...")` 或把密钥写进仓库。此类问题适合用审查判断在 PR 阶段拦截。

## What to Check

### 1. SQL 方言与可移植性

- 新增 **`db.session.execute(text("..."))`**、`raw SQL` 字符串或原生驱动调用时：是否使用 **仅 MySQL 或仅 SQLite** 的语法/函数且无环境分支说明。
- **GOOD**：优先 SQLAlchemy ORM/查询 API；若必须原生 SQL，有注释说明为何限制环境，或封装在明确仅生产路径。
- **BAD**：随意使用 `JSON_EXTRACT`、`ON DUPLICATE KEY`、仅 SQLite 的 `AUTOINCREMENT` 细节等而未说明对另一引擎的影响。

### 2. 配置与密钥

- PR 是否新增或修改包含 **真实密码、JWT secret、云 API Key** 的提交（`.env`、真实 `DATABASE_URL` 等）。应使用占位符 + [backend/QUICKSTART.md](backend/QUICKSTART.md) 类文档说明。
- **GOOD**：`.env.example` 或文档中的占位符；密钥仅从环境变量读取。
- **BAD**：可识别为生产强度的 secret 出现在源码或默认配置中。

### 3. CORS / JWT 生产适宜性（轻量）

- 若 PR 改动 **CORS 通配**、`JWT_SECRET_KEY` 默认值、`DEBUG=True` 作为默认运行方式：是否在合并主分支语境下明显不安全（需说明或限制在 development config）。

## Key Files

- `backend/app/config.py`
- `backend/app/models/**/*.py`
- `backend/app/services/**/*.py`
- `backend/init_db.py`
- `.env*`（若出现在 diff 中，重点审查是否误提交真实值）

## Exclusions

- 纯文档更新、前端-only 变更。
- 明确标注为「本地一次性脚本」且不在 `app` 运行时路径内的工具（仍不应含真实密钥）。
