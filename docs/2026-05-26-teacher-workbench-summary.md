# 2026-05-26 教师端工作台沉淀

## 本次完成

- 后端新增教师端聚合能力：`GET /api/v1/teacher/overview?class_id=&period=week|month`，封装在 `TeacherService.get_overview`，路由注册到 `/api/v1/teacher`。
- 教师权限边界：普通教师仅能查看自己负责班级；传入非本人 `class_id` 返回 403；管理员可查看全部班级。
- 聚合接口返回教师工作台所需结构：`teacher`、`classes`、`selected_class`、`metrics`、`heatmap`、`ranking`、`attention_students`、`students`、`recent_activity`。
- `/teacher` 从占位页升级为领航总览，直接消费 `teacherOverview` API，包含班级切换、周期切换、加载态、错误态、空班级态。
- `/trial-arena` 按“试炼中枢”参考图重构为教师视角的试炼管理页，包含试炼卡片、模板库、数据概览、快速创建面板；当前为前端本地交互。
- `/admin` 按“控制中枢”参考图重构为教师端配置页，包含系统设置、AI 教学策略、通知设置、探索规则、数据与安全；当前为前端本地交互。
- `DashboardShell`/`PlexTopbar` 增加 `hideSearch` 紧凑模式，支持教师端自定义顶部状态栏。
- `PlexSidebar` 补齐“控制中枢 / CONTROL CENTER”入口，教师端三张页面统一使用深色 PLEX 框架与橙色强调。

## 验证记录

- 后端：`python -m unittest discover -s tests` 通过。
- 前端：`npm run build` 通过。
- 本地视觉验证：使用 Playwright CLI 截图对照参考图。
  - `output/playwright/teacher-navigator.png`
  - `output/playwright/trial-command.png`
  - `output/playwright/control-center.png`

## 当前边界

- `/teacher` 已接真实后端聚合接口。
- `/trial-arena` 的试炼创建、模板选择、数据概览目前是前端 UI 状态，尚未接真实试炼发布/结算表。
- `/admin` 的规则保存、数据导出、数据备份、缓存清理目前是前端交互提示，尚未接真实配置/审计/导出接口。
- 今日委托仍未持久化；学生端奖励结算仍需后端权限策略与记录表。

## 后续建议

- 新增试炼业务表：试炼定义、班级发布、参与记录、完成结果、奖励结算。
- 新增教师配置接口：班级设置、通知策略、AI 策略、规则配置、数据可见范围。
- 补齐真实种子数据，保证 `teacher001 / teacher123` 登录后有中文班级、学生积分、委托和成就数据。
- 将管理员学生 CRUD 拆到独立入口，避免 `/admin` 既承担控制中心又承担学生管理。
