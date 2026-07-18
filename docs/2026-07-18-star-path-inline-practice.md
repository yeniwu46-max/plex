# PLEX 2026-07-18 星轨内嵌试炼与启动修复

## 今日目标

按计划启动开发环境，在星轨页实现**不跳路由**的内嵌编程试炼，优化地图布局，修复后端启动递归迁移问题，并完成题库审计验证。

## 完成项

### 1. 开发服务器

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 Vite | http://localhost:5180 | `npm run dev` |
| 后端 Flask | http://127.0.0.1:5100 | `.venv\Scripts\python.exe run.py` |

`start.bat --no-browser` 在 PowerShell 下偶发 `parse_args` 标签错误；可用手动双进程启动替代。

### 2. 星轨页内嵌试炼（核心）

**文件**：`frontend/src/views/StarPathLabView.vue`

- 点击「开始编程试炼」或地图宝石 s0–s4 → 在页面底部展开 **内嵌 `PythonTrialWorkspace`**
- 切换小题 **不离开星轨地图**，Toast + 宝石/chip 高亮联动
- AC 通过后调用 `onInlinePassed` 刷新 `question_ac_status`，地图宝石即时更新
- 保留「全屏试炼」入口跳转 `/student/trials/practice/:id`

### 3. 地图美学微调

**文件**：`starPathTrackLayout.ts`、`StarPathTrackCanvas.vue`

- 「递归与迭代」域垂直阶梯：x 间距 22/78 交替，y 步长更均匀
- 节点 orb 60px（当前节点 68px），标签区 max-width 128px
- 域切换时 `fitView()` 自动居中（已有逻辑保留）

### 4. 后端启动与题库审计

**问题**：`audit_practice_questions.py` 内 `create_app()` 递归调用导致启动卡死。

**修复**：
- `audit_and_migrate()` 优先使用已有 Flask app context
- 脚本独立运行时自动 `sys.path` 注入 backend 根目录

**审计结果**：439 道 coding 题扫描，`updated: 0`（题干与 test_cases 已规范化）。

## 验证

| 检查项 | 结果 |
|--------|------|
| `GET /api/v1/health` | healthy |
| `pytest` practice/mistakes/progress | 9/9 通过 |
| `npm run build` | 通过 |

## 后续建议

1. 修复 `start.bat` 在 PowerShell 下的 `parse_args` 兼容性
2. 内嵌试炼面板可加「折叠/展开」记忆用户偏好
3. 全屏试炼与内嵌试炼代码状态同步（sessionStorage 已有部分支持）

## 分支

- `codex/multi-ai-assistents`
