# PPPLEX — A3 答辩导航站

**Presentation Plex**：只读答辩导航，用于讲解项目结构与跳转本地 A3 演示。不连接数据库、不修改业务代码。

## 内容源

| 文件 | 用途 |
|------|------|
| [`../docs/defense/A3-PLEX-答辩项目说明.md`](../docs/defense/A3-PLEX-答辩项目说明.md) | 完整答辩文稿（给人读 / 给 AI 生成材料） |
| [`../docs/defense/manifest.json`](../docs/defense/manifest.json) | PPPLEX 结构化数据（章节、演示链接、截图） |

校验脚本（可选）：

```bash
node scripts/defense-md-to-manifest.mjs
```

## 答辩当天启动

### 终端 1 — A3 后端

```bash
cd backend
python init_db.py    # 仅首次或需重置种子数据
python run.py        # http://127.0.0.1:5000
```

### 终端 2 — A3 前端（现场演示）

```bash
cd frontend
npm run dev          # http://localhost:5173
```

### 终端 3 — PPPLEX（讲稿导航）

**Windows 最快**：双击 [`ppplex/start.bat`](start.bat)，会自动 `npm install` 并启动。

或命令行：

```bash
cd ppplex
npm install          # 仅首次
npm run dev          # http://localhost:5174
```

**无法打开页面时请先确认**：

1. 终端里出现 `VITE ... ready` 且显示 `Local: http://localhost:5174/`（服务必须保持运行，关掉终端就停）。
2. 使用 **http://localhost:5174/**（配置已绑定 `0.0.0.0`，`127.0.0.1:5174` 也可用）。
3. 若 5174 被占用，Vite 会自动换端口，请看终端实际打印的地址。
4. 未装依赖时会失败：在 `ppplex` 目录执行 `npm install`。

推荐布局：**副屏或第二窗口全屏 PPPLEX**，需要操作时点击「演示」按钮打开 A3 对应页面。

## 环境变量

`ppplex/.env`：

```env
VITE_A3_BASE=http://localhost:5173
```

若前端改端口，同步修改此项。

## 测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 教师 | `teacher001` | `teacher123` |
| 学生 | `student001` | `student123` |
| 管理员 | `admin` | `admin123` |

## 答辩脚本（10 分钟推荐）

在 PPPLEX 侧栏打开 **答辩脚本**，按勾选清单操作；或直接使用 A3：

1. `student001` → `/student/discovery` 探索舱
2. `/student/daily` 今日委托 / 教师题目
3. 探索舱补给站紧急任务
4. `/student/archives` 档案记录
5. `/student/star-path` 星轨学域
6. `teacher001` → `/teacher/trials` 发布试炼
7. `/teacher` 领航总览

## 断网 / 后端不可用预案

1. **仅 PPPLEX**：仍可讲解首页、架构、FAQ 与截图（`public/assets/` 已内置设计稿）。
2. **不要点「演示」**：链接依赖本地 `5173` 前端。
3. **备用**：打开 `docs/defense/A3-PLEX-答辩项目说明.md` 或仓库 `picture/` 原图对照讲解。

## 构建静态页（可选）

```bash
cd ppplex
npm run build
npm run preview    # 预览 dist
```

可将 `dist/` 拷贝至 U 盘；演示链接仍指向本机 `localhost:5173` 时需提前启动 A3 前端。

## 截图资源

答辩用图位于 `ppplex/public/assets/`（从仓库 `picture/` 复制）。更新设计稿后重新复制对应 PNG 即可。
