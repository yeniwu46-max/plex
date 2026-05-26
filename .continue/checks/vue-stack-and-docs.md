---
name: Vue 栈与文档一致性
description: 防止主工程偏离已定 Vue 3 技术栈，并捕捉 AGENTS/技术选型文档与仓库事实（如 frontend/ 是否存在）明显脱节。
---

# Vue 栈与文档一致性

## Context

本仓库在 [AGENTS.md](AGENTS.md) 与 [技术选型与约定.md](技术选型与约定.md) 中已定案：**正式前端 = Vue 3 + Vite + Naive UI + Pinia + Axios**；不以 React 作为长期主栈。文档里仍有一段写「根目录当前无 `frontend/`」类表述，而仓库可能已有 `frontend/`。这类问题无法由 `vue-tsc` 或 ESLint 单独覆盖，需要人工判断「栈是否漂移、文档是否误导新成员」。

## What to Check

### 1. 框架与依赖漂移

- 在 `frontend/` 下新增或升级的依赖：是否引入 **React / Next / Angular** 作为主 UI 框架，或把主应用迁出 Vue（除非 PR 明确说明为「外部参考、不入主工程」且范围隔离）。
- **GOOD**：`package.json` 中 UI 以 `vue`、`naive-ui`、`pinia`、`axios`、`vite` 为主。
- **BAD**：在正式 `frontend/src` 新增 `.tsx` 主应用、`react-dom` 作为运行时依赖且无「仅参考」说明。

### 2. 与定案文档对齐

- 若 PR **新增或显著扩展** `frontend/`，检查 [AGENTS.md](AGENTS.md)「仓库现状」、[技术选型与约定.md](技术选型与约定.md)「仓库事实」是否仍写「无 `frontend/`」等**与事实矛盾**的句子；若矛盾，应视为需同步文档或在 PR 中说明 intentional lag。
- **GOOD**：文档与目录结构一致，或 PR 正文写明后续跟进的文档任务。
- **BAD**：大量 Vue 代码已合入，根索引文档仍断言不存在前端目录。

### 3. 与 UI 规范意图一致（轻量）

- 新页面是否明显违背 [frontend_design_v2.md](frontend_design_v2.md) 中已强调的交互/游戏化方向（仅作**明显**违背判断，不要求逐像素对照）。

## Key Files

- `frontend/package.json`
- `frontend/src/**/*.vue`
- `AGENTS.md`
- `技术选型与约定.md`
- `frontend_design_v2.md`（抽样对照）

## Exclusions

- 仅修改后端、仅改 Markdown 设计稿、或明确标注为「外部原型」且未并入 `frontend/` 的变更。
- 依赖的补丁版本升级且不改变框架族。
