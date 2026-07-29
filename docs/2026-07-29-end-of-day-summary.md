# PLEX 2026-07-29 日终沉淀总结

日期：2026-07-29  
分支：`codex/multi-ai-assistents`  
范围：学生端壳层与资源可见性、教师端审核/文件/学情交互、管理员大盘与智能体编排、讯飞星火多场景接入

> 同日另有专项文档：[2026-07-29-stream-ux-and-auto-approve.md](./2026-07-29-stream-ux-and-auto-approve.md)（流式体验与资源自动审批）。本文汇总当日后续联调与 UI 闭环。

## 一、今日目标

1. 消除学生端重复导航、侧栏滚动跟随、个性化资源「有数无列表」等问题。  
2. 教师端资源审核卡片化、试炼任务仓、作业打分、需跟进学员可钻取。  
3. 管理员端大盘数据真实化、权限设置合并、智能体卡片化与运行试炼钻取。  
4. 小E / 补给站 / 试炼分析优先走讯飞星火，并保证失败可回退。

## 二、学生端

### 2.1 壳层与导航

- **根因**：`KeepAlive` 多页通过 `Teleport` 向同一工具栏挂载 `StudentSectionTabs`，停用页不卸载 → 双行「学习画像 / 成长档案 / 账号设置」；整页滚动导致侧栏跟着滚。
- **修复**：
  - 分区 tabs 仅在 `StudentShellLayout` 渲染一次。
  - `DashboardShell` 锁高：`overflow: hidden`，仅 `main-body` 滚动；侧栏 sticky；工具条提高 `z-index`，避免被成长页标题盖住。
  - 全局 `html/body/#app/.app-root` 高度 100%，保证壳层可固定。

### 2.2 个性化资源「看不到」

- **根因**：接口已返回 `approved + pending_review`（演示约 163 条）；前端类型下拉残留「思维导图」、流水线占满首屏、折叠未展开导致「有 41 可学习却像空白」。
- **修复**：切回重置「全部类型」；完成后收起流水线；知识点组常显卡片；资源在本页「已生成资源」左侧列表。

### 2.3 星轨 / 画像 / 登录 / 补给站

- 同步态组件 `PlexSyncState`：轨道+脉冲；有缓存软刷新。
- 星域节点切换：「当前所在」、选中框、菱形高亮与入场动效跟随选中节点。
- 「记住我」：`loginAccountHistory` 本地历史账号联想。
- 边界补给站：画像 + 最近练习 → 星火出 3 题；失败本地题库回退。凭证键：`IFLYTEK_SPARK_SUPPLY_CREDENTIALS`。

### 2.4 小E 对话

- 供应商链优先：星火 → 星辰 Agent → DeepSeek → 规则。
- 流式超时放宽；上下文失败不阻塞首字；前端滚动 `rAF` 节流。
- 凭证：`IFLYTEK_SPARK_CREDENTIALS`（与试炼/补给站隔离）。

## 三、教师端

### 3.1 资源审核

- 去掉风险原因 tag 墙；每条待审资源一张可点卡片。
- 详情弹窗展示 AI 六步报告 + 人工批准/驳回。
- AI 审核放宽：题量不足、缺答案、compile 失败等 **FAIL → WARNING**；仅安全/幻觉类硬 FAIL 才 REJECT。

### 3.2 试炼中枢

- Tab：试炼管理 | 我的模板 | **文件管理**（上传三卡 + 学生提交预览）。
- 试炼详情「任务仓」三 Tab：题目统计 / 题目预览 / 学生作答明细。
- 「小E帮分析」：`POST /v1/teacher/trials/:id/ai-analyze`；星火超时与前端请求超时对齐，失败本地统计回退。凭证：`IFLYTEK_SPARK_TRIAL_CREDENTIALS`。

### 3.3 学情与成员

- 班级选择 `localStorage` 持久化；学情诊断 `sessionStorage` 按班缓存，刷新不重跑。
- 「影响学生」：query 路由避免 404；表含班级、学号（username）、姓名、答错类型。
- 「需跟进学生」与 Explorer「一键查看」共用弹窗。
- 热力图 / 排行榜 / 成员列表点击出资料卡 + 最近练习。
- 学生提交文件预览后可打分：滑条 0–100 + 快捷 60/70/80/90；`PUT /v1/class-files/score`。

## 四、管理员端

### 4.1 中央总控数据真实化

- `GET /v1/admin/dashboard?period=` 返回进度、活跃趋势、**storage**、**alerts**。
- 存储「查看详情」弹窗展示分解与业务量明细。
- 「运行试炼」可钻取：教师 → 班级 → 试炼作答（题目正确率 / 学生进度）。

### 4.2 权限与控制

- `AdminGovernanceComboPanel`：班级变更审批 + 系统设置同组件 Tab 切换。
- **移除**系统设置中的「AI 策略开关」模块。

### 4.3 智能体编排

- 检查智能体改为独立小卡片：日/周用量、额度、置信度；点开详情。
- 协同流程保留真实调用边；节点可点查看状态（`PlexAgentFlow`）。
- 模块运行状态增加脉冲与状态点动效。

## 五、后端 API / 配置要点（新增或调整）

| 能力 | 端点 / 配置 |
|------|-------------|
| 大盘（含周期） | `GET /v1/admin/dashboard?period=today\|week\|month` |
| 试炼钻取 | `GET /v1/admin/trials/teachers`、`.../teachers/:id/classes`、`.../classes/:id/stats` |
| 影响学生 | `GET /v1/knowledge-graph/class/{id}/affected-students?node_id=` |
| 试炼 AI 分析 | `POST /v1/teacher/trials/:id/ai-analyze` |
| 作业打分 | `PUT /v1/class-files/score` |
| 星火凭证 | `IFLYTEK_SPARK_CREDENTIALS` / `_TRIAL_` / `_SUPPLY_`（仅本地 env，勿入库） |

## 六、主要新增文件

- `frontend/src/components/common/PlexSyncState.vue`
- `frontend/src/components/admin/AdminGovernanceComboPanel.vue`
- `frontend/src/components/admin/AdminRunningTrialsDrilldown.vue`
- `frontend/src/components/teacher/AttentionStudentsModal.vue`
- `frontend/src/components/teacher/ExplorerProfileModal.vue`
- `frontend/src/utils/loginAccountHistory.ts`
- `docs/2026-07-29-end-of-day-summary.md`（本文）

## 七、验证清单（建议本地）

1. 重启后端加载新 env；强制刷新前端。  
2. 学生「我的」多切页：tabs 仅一行；侧栏滚动不跟随。  
3. 个性化资源：类型选「全部类型」，左侧出现知识点卡片。  
4. 教师：资源卡片进详情；文件管理预览/打分；试炼三 Tab + 小E分析。  
5. 管理员：大盘指标随周期变化；运行试炼钻取；编排卡片用量；权限 Tab。  
6. 登录勾选「记住我」后账号联想；补给站新会话出题。

## 八、已知限制 / 后续

- 星火密钥有效性需线上联调确认；星辰 Agent 的 `FLOW_ID` 若换应用需同步。  
- 作业打分当前侧车 JSON，非独立库表。  
- 学情诊断缓存在 `sessionStorage`，关标签页清空。  
- 历史已标异常资源需再跑智能审核才按新规则重评。  
- 未做完整浏览器 E2E；`vue-tsc` 当日管理员相关改动已通过。

## 九、提交说明

- 不提交 `.env` / `.env.spark.local` 等真实密钥。  
- 不纳入大型 submission artifacts 目录。  
- 与同日流式/自动审批专项文档一并沉淀，便于答辩与复盘。
