# 2026-05-27 学生端探索链路沉淀

## 本次完成

### 1. 教师试炼 → 学生题目下发

- **数据表**：`trial_questions`（试炼题目）、`trial_question_progress`（学生作答进度）。
- **题目生成**：教师创建/发布试炼（`POST /api/v1/teacher/trials`、`* /publish`）时，按 `knowledge_key` 从题库随机生成 **3 道选择题**（`QuestionGenerator`）。
- **学生 API**：
  - `GET /api/v1/student/assignments` — 本班进行中试炼的待做题目；
  - `POST /api/v1/student/assignments/<question_id>/answer` — 提交答案，答对自动推进今日委托 `fragment-repair`。
- **前端**：
  - 探索舱「待修复碎片」显示待做题数（`StarFieldMap`）；
  - 今日委托页顶部「教师布置 · 知识碎片」面板（`TeacherAssignmentPanel`）；
  - `GET /api/v1/daily-quests/today` 响应增加 `teacher_assignments` 字段。

### 2. 边界条件补给站 · 紧急任务

- **数据表**：`emergency_mission_sessions`、`emergency_mission_questions`。
- **逻辑**：根据学生近期试炼掌握情况选取薄弱知识点，随机 3 题；**全部答对**发放 +55 XP；提交后立即展示正确答案与解析。
- **学生 API**：
  - `POST /api/v1/student/emergency-missions/start` — 生成/恢复进行中任务；
  - `POST /api/v1/student/emergency-missions/<session_id>/submit` — 批量提交答案。
- **前端**：
  - 探索舱星图「边界条件补给站」弹出 `EmergencyMissionModal`；
  - 探索档案新增「补给站紧急任务」记录区，成长轨迹同步展示（`archive-insights.emergency_missions`）。

### 3. 星轨路径 · 六大学域与知识点导航

- **学域标签**：全部星域、语言基础、算法基础、动态规划、计算几何、图论、数据结构（`frontend/src/data/starPathDomains.ts`）。
- **交互**：标签/星域概览卡片/路径节点点击 → 切换学域、更新 URL（`?domain=&kp=`）、右侧详情面板展示知识点详解；非算法学域为 4 节点路径图；算法基础保留 01–07 星轨节点与 Python 试炼关联。
- **内嵌试炼**：在星轨页点击「开始编程试炼」于当前页打开 `PythonTrialWorkspace`（`?practice=1&q=`），不跳转试炼关卡；无静态题的知识点由前端模板随机生成编程题（`sessionStorage` 按 `kp.id` 缓存）。
- **后端**：`StudentProgressService.DOMAIN_CATALOG` 与前端六域对齐，`GET /api/v1/student/learning-path` 返回对应进度。

### 4. 开发与运维修复

- **Vite 代理**：默认指向 `http://127.0.0.1:5000`（`vite.config.ts`、`frontend/.env.development` 的 `VITE_API_PROXY`），修复前端 502。
- **Flask（Windows）**：`run.py` 在 Windows 关闭 debug 重载器，避免 5000 端口双进程导致 API 404。
- **init_db**：`RolePermission` 改为 `role.permissions` 多对多写法，与当前模型一致。

## 新增/变更 API 一览

| 方法 | 路径 | 角色 | 说明 |
|------|------|------|------|
| GET | `/api/v1/student/assignments` | student | 教师试炼待做题目 |
| POST | `/api/v1/student/assignments/<id>/answer` | student | 提交单题答案 |
| POST | `/api/v1/student/emergency-missions/start` | student | 开始紧急任务 |
| POST | `/api/v1/student/emergency-missions/<id>/submit` | student | 提交紧急任务（3 题） |
| GET | `/api/v1/daily-quests/today` | student | 含 `teacher_assignments` |
| GET | `/api/v1/student/archive-insights` | student | 含 `emergency_missions` 历史 |
| GET | `/api/v1/student/learning-path` | student | 六大学域进度 |

## 验证记录

```bash
cd backend
python -m unittest discover -s tests -p "test_assignments.py" -v
python -m unittest discover -s tests -p "test_emergency_mission.py" -v
python -m unittest discover -s tests -p "test_student_progress.py" -v
```

本地启动：

```bash
# 后端
cd backend && python run.py

# 前端
cd frontend && npm run dev
```

- 前端：http://localhost:5173  
- 后端：http://127.0.0.1:5000  
- 测试账号见 `backend/QUICKSTART.md`（如 `teacher001` / `student001`，密码 `teacher123` / `student123`）

## 体验路径（建议自测）

1. 教师 `teacher001` 在试炼中枢为班级**立即发布**试炼（选择知识点）。
2. 学生 `student001`：探索舱查看「待修复碎片」→ 今日委托作答教师题目。
3. 学生点击「边界条件补给站」完成紧急任务 → 探索档案查看记录。
4. 学生打开星轨路径，切换六大学域标签，点击知识点查看详情与 URL 跳转。

## 当前边界

- 题目内容为**规则题库随机**，尚未接大模型生成或教师自定义题干编辑。
- 紧急任务可重复开启新会话；未做「每日一次」限流。
- 非「算法基础」学域暂无独立代码试炼题，知识点以阅读+标签导航为主；关联试炼仅算法域部分 `questionId`。
- 教师端星域观测标签仍为旧命名处时，与学生端六域展示可能不完全一致（可按需下一轮统一）。

## 后续建议

- 试炼完成时自动推进 `trial-challenge` 委托进度。
- 教师可预览/编辑下发题目，或按班级覆盖题库。
- 紧急任务与错题本（驿站）薄弱点联动推荐。
- 将 `backend/README.md` / `backend_api_design.md` 增量同步上述端点与表结构。

## 关键文件索引

| 模块 | 路径 |
|------|------|
| 试炼题目模型 | `backend/app/models/trial_question.py` |
| 紧急任务模型 | `backend/app/models/emergency_mission.py` |
| 题库与生成 | `backend/app/services/question_generator.py` |
| 学生作答 | `backend/app/services/assignment.py` |
| 紧急任务服务 | `backend/app/services/emergency_mission.py` |
| 星轨学域数据 | `frontend/src/data/starPathDomains.ts` |
| 星轨页 | `frontend/src/views/StarPathLabView.vue` |
| 紧急任务弹窗 | `frontend/src/components/discovery/EmergencyMissionModal.vue` |
| 教师题目面板 | `frontend/src/components/student/TeacherAssignmentPanel.vue` |
