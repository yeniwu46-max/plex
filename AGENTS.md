# 仓库说明（给 AI 与新成员）

**最后更新**：2026-05-27

本文档是**新会话入口**：用户只说「了解项目」时，请先按下方阅读顺序加载上下文，再回答或改代码，避免默认成 React；正式前端在 [`frontend/`](frontend/)（Vue 3 + Vite）。

---

## 项目一句

**个性化学习系统（代号 A3）**，前后端分离：**Flask 后端**（`backend/`）+ **Vue 3 前端**（`frontend/`）；接口与表设计见 Markdown 设计稿。

---

## 技术选型（结论，必读）

| 层级 | 定案 | 说明 |
|------|------|------|
| 前端 | **Vue 3 + Vite + Naive UI + Pinia + Axios**；动效可选 **motion-v**（见 `技术选型与约定.md` 第 1.2 节） | 本仓库**正式前端唯一目标栈**。用户未写明「仅保留 React 原型 / 参考」时，**不要**把新页面、新功能默认写成 React。 |
| 后端 | **Flask + SQLAlchemy**（Flask-SQLAlchemy） | 业务与 API 在 `backend/app/`。 |
| 数据库 | 生产 **MySQL**；本地可 **SQLite** | 本地启动见 `backend/QUICKSTART.md`。 |
| 认证 | **JWT**（Access + Refresh），非 Session 为主 | 与多端、前后端分离一致。 |

定案细节、与 AI 工具偏 React 的协作约定见：**[技术选型与约定.md](技术选型与约定.md)**（与 `TECH_PLAN.md` 冲突时，**以技术选型与约定为准**，并提醒维护者同步总纲）。

---

## 仓库现状（避免误判）

- **后端代码**：[`backend/`](backend/)，REST JSON；API 路径以 **`/api/v1`** 为前缀（细节以 [backend_api_design.md](backend_api_design.md) 为准）。本地默认 `http://127.0.0.1:5000`（见 [backend/QUICKSTART.md](backend/QUICKSTART.md)）。
- **前端源码**：[`frontend/`](frontend/)（Vue 3 + Vite + Naive UI + Pinia + Axios）。开发时 `npm run dev`（默认 `http://localhost:5173`），经 Vite 代理访问 `/api` → 后端（代理目标见 `frontend/.env.development` 的 `VITE_API_PROXY`，默认 `http://127.0.0.1:5000`）。UI/UX 与游戏化规范见 [frontend_design_v2.md](frontend_design_v2.md)。外部 React 原型仅作参考，正式功能以 Vue 实现，见《技术选型与约定》。
- **教师端路由**：`/teacher`（领航总览）、`/teacher/starfield`（星域观测）、`/teacher/explorers`（Explorer 档案）；试炼/设置入口 `/trial-arena`、`/admin`。班级数据由 [`TeacherOverviewLayout.vue`](frontend/src/layouts/TeacherOverviewLayout.vue) 注入，勿在页面组件顶层对 Shell 使用 `inject`。
- **学生端近期能力**（2026-05-27 沉淀见 [docs/2026-05-27-student-exploration-summary.md](docs/2026-05-27-student-exploration-summary.md)）：教师发布试炼 → 探索舱/今日委托题目；补给站紧急任务；星轨六大学域知识点导航（`/student/star-path`）。

---

## 新会话建议阅读顺序（给 AI）

1. [技术选型与约定.md](技术选型与约定.md) — 技术定案与 React/Vue 约定  
2. [TECH_PLAN.md](TECH_PLAN.md) — 架构、阶段目标、模块总览  
3. 按需：[backend_api_design.md](backend_api_design.md)（接口与表）、[backend/QUICKSTART.md](backend/QUICKSTART.md)（安装与测试账号）、[backend/README.md](backend/README.md)（模块与端点列表）、[docs/2026-05-27-student-exploration-summary.md](docs/2026-05-27-student-exploration-summary.md)（学生探索链路变更摘要）

**不要**把大段 API 表或设计稿复制进对话；用 Read 工具读上述文件即可。

---

## AI / Agent 可选 Python 库（本机）

任务涉及 **LangGraph / E2B / LlamaIndex / CrewAI** 时，先读 **[docs/AI-Agent-Python栈.md](docs/AI-Agent-Python栈.md)**：其中写明当前环境**已装与未装**、适用场景与 CrewAI 在 Windows + Python 3.14 下的安装注意。匹配场景时可直接按该文档选用库，无需重复确认是否安装。

---

## 维护

变更框架、数据库或认证策略时，请同步更新 **技术选型与约定.md** 与本文件表格，并检查 **TECH_PLAN.md** 是否一致。

---

## Checks（Continue PR 审查）

本仓库在 `.continue/checks/` 下维护面向 **Continue Checks** 的 Markdown 检查项；在 PR 上可作为全量 Agent 审查运行（亦可在 [Mission Control](https://continue.dev) 连接 GitHub 后自动跑）。

**提 PR 前（本地）**：安装 Continue 的 `/check` skill 后，在支持的环境中对当前 diff 执行 `/check`，对照全部 `.continue/checks/*.md` 验证；未通过须在 PR 中说明或修复。详见 [Running checks locally](https://docs.continue.dev/checks/running-locally)。

```bash
npx skills add continuedev/skills --skill check
```

当前检查文件：

- `vue-stack-and-docs.md` — Vue 定案栈与 AGENTS/技术选型文档是否一致  
- `flask-api-jwt-shape.md` — `/api/v1`、统一 JSON 响应、JWT/权限装饰器是否合理  
- `db-portability-secrets.md` — SQLite/MySQL 可移植性与密钥卫生
