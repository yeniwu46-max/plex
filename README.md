# PLEX Universe / A3 个性化学习系统

PLEX Universe 是一个面向编程学习场景的个性化学习平台，项目代号 A3。它把学生端、教师端和管理端拆成清晰的三类工作台：学生完成每日委托和试炼，教师观察班级学习状态并发布试炼，管理员维护平台策略与系统配置。

当前仓库采用前后端分离架构：

- 前端：Vue 3 + Vite + Naive UI + Pinia + Axios
- 后端：Flask + SQLAlchemy + JWT
- 数据库：生产建议 MySQL，本地开发可直接使用 SQLite
- API：REST JSON，统一前缀 `/api/v1`

## 功能概览

### 学生端

- `/student`：学生首页，聚合 XP、等级、班级排名、今日委托和成长摘要。
- `/student/discovery`：探索舱，连接知识星域与班级试炼入口。
- `/student/daily`：今日委托，支持任务进度、奖励反馈与每日完成状态。
- `/student/trials`：学生试炼，支持查看、参与和完成教师发布的班级试炼。
- `/student/archives`：探索档案，展示成长轨迹、能力分布和成就收藏。
- `/student/star-path`、`/student/messenger`、`/student/control`：学习路径、驿站与学生控制页。

### 教师端

- `/teacher`：领航总览，聚合班级指标、热力图、排名、关注学生与近期动态。
- `/teacher/starfield`：星域观测，按知识领域观察班级风险与掌握情况。
- `/teacher/explorers`：Explorer 档案，查看学生画像、成长曲线、委托、知识与试炼记录。
- `/teacher/trials`：试炼中枢，创建、发布、编辑和查看班级试炼。

### 管理端

- `/admin`：控制中枢，仅管理员可访问。用于平台配置、AI 策略、通知开关、试炼规则和数据安全设置。

## 项目结构

```text
.
├── backend/                    # Flask 后端服务
│   ├── app/
│   │   ├── models/             # SQLAlchemy 模型
│   │   ├── routes/             # REST API 路由
│   │   ├── services/           # 业务服务层
│   │   └── utils/              # JWT、响应、装饰器等工具
│   ├── tests/                  # 后端单元测试
│   ├── init_db.py              # 初始化数据库
│   └── run.py                  # 本地启动入口
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── api/                # Axios API 封装
│   │   ├── components/         # 通用与业务组件
│   │   ├── layouts/            # 页面布局
│   │   ├── router/             # 三端路由与权限守卫
│   │   ├── stores/             # Pinia 状态
│   │   └── views/              # 页面视图
│   └── package.json
├── docs/                       # 工作计划、阶段总结和环境说明
├── backend_api_design.md       # API 与数据表设计
├── frontend_design_v2.md       # 前端 UI/UX 规范
├── 技术选型与约定.md            # 技术栈事实来源
└── TECH_PLAN.md                # 项目技术方案总纲
```

## 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python init_db.py
python run.py
```

默认后端地址：`http://127.0.0.1:5000`

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认前端地址：`http://localhost:5173`

前端开发环境通过 Vite 代理访问 `/api`，转发到 Flask 后端。

## 测试账户

初始化数据库后可使用以下账号登录：

| 角色 | 用户名 | 密码 | 入口 |
| --- | --- | --- | --- |
| 管理员 | `admin` | `admin123` | `/admin` |
| 教师 | `teacher001` | `teacher123` | `/teacher` |
| 学生 | `student001` | `student123` | `/student` |
| 学生演示数据 | `explorer01` - `explorer10` | `student123` | `/student` |

如需补充教师班级演示数据：

```bash
cd backend
python seed_li_class_students.py
python seed_incentive_achievements.py
python seed_trials_demo.py
```

## 常用命令

### 前端

```bash
cd frontend
npm run dev
npm run build
```

### 后端

```bash
cd backend
python run.py
python -m unittest discover -s tests
```

## API 响应格式

成功响应：

```json
{
  "code": 0,
  "message": "操作成功",
  "data": {}
}
```

错误响应：

```json
{
  "code": 40001,
  "message": "错误信息",
  "data": null
}
```

认证请求使用 JWT：

```text
Authorization: Bearer <access_token>
```

## 开发约定

- 新前端功能默认写在 `frontend/`，使用 Vue 3，不引入 React 作为正式栈。
- 三端页面保持路由隔离：学生端 `/student/...`，教师端 `/teacher/...`，管理端 `/admin`。
- 需要认证的 API 保持 `/api/v1` 前缀和统一 JSON 响应结构。
- 提交前建议运行：

```bash
cd backend && python -m unittest discover -s tests
cd ../frontend && npm run build
```

## 文档入口

- [技术选型与约定.md](技术选型与约定.md)：当前技术栈事实来源。
- [TECH_PLAN.md](TECH_PLAN.md)：架构、阶段目标和模块总览。
- [backend_api_design.md](backend_api_design.md)：API 与数据表设计。
- [backend/QUICKSTART.md](backend/QUICKSTART.md)：后端本地启动、测试账号和种子脚本。
- [frontend_design_v2.md](frontend_design_v2.md)：前端 UI/UX 与游戏化设计规范。
- [docs/2026-05-26-teacher-workbench-summary.md](docs/2026-05-26-teacher-workbench-summary.md)：教师端、试炼与三端隔离阶段总结。

## 当前状态

项目处于教学平台 MVP 迭代阶段，已具备用户认证、三端路由、教师聚合看板、学生任务/试炼闭环、管理端配置页和基础测试覆盖。生产部署前仍建议补齐数据库迁移、权限审计、License、CI 和更完整的环境变量示例。
