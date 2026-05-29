# 2026-05-29 功能缺口补全 & 静态数据三端同步沉淀

**主题**：补全教学闭环缺口，将 hardcode/mock 数据对接后端，修复三端同步断点  
**前置提交**：`66f2f43`（开源组件接入：Monaco / G6 / ECharts / Vue Flow）

---

## 一、本次工作概览

| 阶段 | 范围 | 状态 |
|------|------|------|
| 第一阶段 | 功能缺口补全（委托联动、紧急任务限流、教师题预览） | ✅ |
| 第二阶段 P0 | 已有 API 纯前端对接（设置、筛选、碎片轮询） | ✅ |
| 第二阶段 P1 | 跨端同步（公告、晨间/夜间委托、档案去 mock） | ✅ |
| 第二阶段 P2 | 新后端聚合 API（教师/学生/管理员图表与大盘） | ✅ |

---

## 二、第一阶段：功能缺口补全

### C — 教师试炼题目预览

- **文件**：`frontend/src/components/teacher/TeacherTrialDetailPanel.vue`
- **改动**：在题目统计与学生明细之间增加折叠式「题目预览」，展示题干、ABCD 选项（正确答案高亮）
- **后端**：无改动（`GET /teacher/trials/:id/detail` 已返回 `questions`）

### A — 今日委托奖励联动

- **后端**：`backend/app/services/trial.py` — `complete_trial` 后调用 `DailyQuestService.advance_progress(user_id, 'trial-challenge')`
- **前端**：
  - `TeacherAssignmentPanel.vue` — 答题成功后 `auth.syncProfile` 刷新侧栏 XP
  - `DailyQuestView.vue` — 委托推进 / 全勤奖励后同步 profile
- **类型**：`IncentiveFeedbackPayload` 增加 `total_points` 字段

### B — 紧急任务每日一次限制

- **后端**：
  - `emergency_mission.py` — `start_session` 校验今日是否已完成
  - `student_progress.py` — 新增 `GET /api/v1/student/emergency-missions/today-status`
- **前端**：
  - `DiscoveryCabinView.vue` — 挂载时查今日状态
  - `StarFieldMap.vue` — 补给站按钮 `disabled` +「今日已完成」文案
  - `emergencyMission.ts` — `fetchEmergencyTodayStatus`

---

## 三、第二阶段 P0：已有 API 前端对接

| 任务 | 说明 | 关键文件 |
|------|------|----------|
| Admin 系统设置 | 治理 Tab 加载/保存试炼规则、AI 策略、通知开关 | `AdminHomeView.vue`, `adminSettings.ts` |
| Explorer 域筛选 | `domainFilter` 参与 `filteredStudents` 过滤 | `ExplorerListPanel.vue` |
| 探索舱碎片轮询 | `onMounted` + 30s 轮询 + `onActivated` 刷新 | `DiscoveryCabinView.vue` |

---

## 四、第二阶段 P1：跨端同步

### 学生接收管理员公告

- **后端**：`GET /api/v1/student/announcements`（`announcements.py`）
- **前端**：`useStudentNotificationSync.ts` — `syncAnnouncements` + 轮询合并公告到 `notifications` store

### 晨间 / 夜间委托真实触发

- 进入探索舱 → 自动 `advanceDailyQuest('morning-launch')`（幂等）
- 进入探索档案 → 自动 `advanceDailyQuest('night-summary')`
- 今日委托页：`morning-launch` / `night-summary` 卡片只读，提示访问对应页面完成

### 档案去掉 mock 兜底

- **文件**：`ExplorationArchivesView.vue`
- **改动**：移除「张子轩」等 `archivesMock` 假数据合并；API 失败显示错误态 + 重试；仅用真实 overview + archive-insights

---

## 五、第二阶段 P2：新后端聚合 API

### 教师班级统计

```
GET /api/v1/teacher/class-stats?class_id=
```

- **服务**：`TeacherService.get_class_stats` — 从 `trial_question_progress` 按知识点聚合掌握度与错题分布
- **前端**：`TeacherHomeView.vue` 柱状图 / 饼图接真实数据

### 学生能力统计

```
GET /api/v1/student/ability-stats
```

- **服务**：`StudentProgressService.get_ability_stats` — 雷达五维 + 近 7 日练习次数/正确率
- **前端**：`StudentControlView.vue` 雷达图 / 折线图接真实数据

### 管理员大盘

```
GET /api/v1/admin/dashboard
```

- **服务**：`AdminDashboardService.get_dashboard` — 活跃学生、教师数、试炼数、完成率、健康度等
- **前端**：`AdminHomeView.vue` 中央总控指标卡片与进度条接真实数据

---

## 六、新增 / 主要修改文件

### 后端新增

| 文件 | 说明 |
|------|------|
| `backend/app/services/admin_dashboard.py` | 管理员大盘聚合 |

### 后端修改

| 文件 | 说明 |
|------|------|
| `trial.py` | 试炼完成推进 trial-challenge 委托 |
| `emergency_mission.py` | 每日一次限制 + today_status |
| `student_progress.py` | ability-stats 端点 |
| `teacher.py` | class-stats 端点 |
| `admin_settings.py` | dashboard 端点 |
| `announcements.py` | student announcements 路由 |

### 前端 API

| 文件 | 新增 |
|------|------|
| `teacherOverview.ts` | `fetchTeacherClassStats` |
| `studentProgress.ts` | `fetchAbilityStats` |
| `adminSettings.ts` | `fetchAdminDashboard` |
| `emergencyMission.ts` | `fetchEmergencyTodayStatus` |

---

## 七、验收建议

1. **教师**：发布试炼 → 学生探索舱碎片数 30s 内刷新；领航总览图表显示真实班级数据
2. **学生**：完成试炼 → 今日委托「试炼挑战」推进；侧栏 XP 即时更新；补给站每日仅可完成一次
3. **管理员**：治理 Tab 保存设置可持久化；中央总控指标来自 `/admin/dashboard`
4. **公告**：管理员发公告 → 学生顶栏通知收到（轮询约 20s）

```bash
cd frontend && pnpm build
cd backend && python -m unittest discover -s tests -p "test_*.py" -v  # 如有
```

---

*文档生成时间：2026-05-29*
