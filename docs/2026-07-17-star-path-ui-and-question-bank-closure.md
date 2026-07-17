# PLEX 2026-07-17 星轨学习 UI 与题库闭环沉淀

## 今日目标

将星轨学习、试炼中心、成长档案、探索舱等学生端核心体验从「可用原型」推进为「可演示、可追踪进度、叙事连贯」的闭环版本；同步修复路由阻塞、题库命名与测试数据质量问题，并放宽试炼解锁门槛以提升可达性。

## 今日完成

### 1. 路由与模块依赖修复

- **问题**：Vue Router 导航报错 `Cannot access 'PYTHON_TRIAL_QUESTIONS' before initialization`，根因为 `pythonTrialQuestions → classArenaQuestions → mockExamSets → pythonTrialQuestions` 循环依赖。
- **方案**：在 `mockExamSets.ts` 新增 `getDefaultMockExamQuestions()` 延迟加载；`classArenaQuestions.ts` 移除顶层常量初始化；`ClassArenaHub.vue` 改为运行时拉取。
- **结果**：试炼/星域页面跳转恢复正常。

### 2. 探索舱星图（Discovery Star Map）

| 能力 | 实现 |
|------|------|
| 粒子背景 | 新建 `StarMapParticles.vue`，原生 Canvas，无额外 npm 依赖 |
| 科技风动效 | 轨道旋转、连线能量流动、节点呼吸光晕、Hub 脉冲 |
| 动效调优 | 全局约 2× 降速（如 orbit 48s→96s、energy-flow 2.8s→5.6s） |
| 连线补全 | 中心 Hub →「边界条件补给站」缺失连线已补 |
| 视口控件 | 移除「适应/重置/滚轮缩放·拖拽平移」可见栏；`useMapViewport` 保留滚轮缩放与拖拽 |

### 3. 星轨学习七大学域重组

原四阶段拆分为 7 个知识分区，前后端注册表与题目生成器同步：

1. 数据与变量  
2. 运算符的使用  
3. 流程控制  
4. 字符串  
5. 列表与字典  
6. 函数  
7. 递归与迭代  

- 前端：`starPathDomains.ts`、`starPathKnowledgeTracks.ts`、`knowledgeNodeRegistry.ts`  
- 后端：`student_progress.py`、`knowledge_node_registry.py`  
- 知识点 ID（如 `stage1-intro`）保持不变，兼容历史进度与试炼题。

### 4. 星轨地图布局与交互

- 引入 **`@dagrejs/dagre`** 按学习顺序自动布局节点。
- 新建 `starPathTrackLayout.ts`：贝塞尔曲线连线、箭头方向、网格背景。
- 「递归与迭代」域采用自定义垂直阶梯布局，避免 dagre S 形拥挤。
- 各域节点按 `nodes` 数组**串联**生成连线；移除轨道地图动画（`path-energy` 等）。
- 地图节点下 **5 颗宝石**与知识点槽位一一对应；点击可切换小题（`selectGem` / `QuestionSlotGems`）。

### 5. 题库智能命名与题干净化

| 模块 | 说明 |
|------|------|
| `questionNaming.ts` | 语义规则 + 精选短标题表；拒绝题干截断式标题 |
| 展示格式 | `P0001 · 星际问候输出`（保留题号前缀 + 8–20 字短名） |
| `questionStemSanitizer.ts` | 剥离题干内嵌 `### 测试样例`、`{[70]}` 及 `**` Markdown |
| 后端 | `practice_question.py` 的 `_normalize_question_payload()`、`_extract_embedded_tests()` |
| DB 迁移 | `audit_practice_questions.py` + 启动时 `db_migrate` 自动审计 |

**示例改善**：`对于任意大于 6 的偶数，均可表示为二…` → `P0051 · 哥德巴赫分解`

### 6. 科幻叙事与每知识点 5 题

- 新建 `explorationNarrative.ts`：16 个知识点各 **5 幕连续剧情**（你与小E 探星），格式 `🛸 星球探险 · 数据星 【第 x/5 幕】`，**不使用 `**` 加粗**。
- `starPathQuestionGenerator.ts`：38 个模板注册表，槽位 ID `gen-{kpId}-s0~s4`。
- 每模板 ≥2 组示例 + ≥2 条测试用例；静态 Python 题补全第二组示例。
- 叙事与任务分离：剧情在 description，示例/测试数据写入结构化字段并在 UI 分区展示。

### 7. 进度宝石与 AC 点亮

- **规则**：每知识点 5 颗宝石 = 5 道题；**AC 几题亮几颗**（`lastPassedAt >= lastFailedAt`）。
- API 新增 `question_ac_status: string[]`（已 AC 题目 ID 列表）。
- 数据流：试炼提交 → `trialMistakeLog` / `StudentMistake` → 学习路径 API → `buildKnowledgeTrack` → 地图宝石渲染。
- 从试炼页返回星轨时 `onActivated` 刷新 AC 状态。

### 8. 试炼中心解锁条件放宽

| 项目 | 原阈值 | 新阈值 |
|------|--------|--------|
| 知识点掌握 (mastery) | 80% | **40%** |
| 星域解锁（前一域进度） | 85% | **40%** |
| 星域「已点亮」 | 85% | **60%** |
| 节点解锁（前一知识点） | 需前置 80% 掌握 | **仅需 1 题 AC** |
| 星域竞技 | Lv.5 | **Lv.2** |
| 自我突破 | Lv.3 | **Lv.1** |
| 深渊试炼 | Lv.5 | **Lv.5**（原 Lv.20） |

常量集中：`frontend/src/constants/starPathUnlock.ts`、`backend/app/constants/star_path_unlock.py`

### 9. 题目切换 UX

- 新建 `QuestionSlotGems.vue`：顶部 s0–s4 胶囊切换，选中高亮 + Toast 提示。
- `StarPathLabView`：宝石/小题 chip 联动；「换一题」按槽位顺序切换。
- `StudentTrialPracticeView`：路由 `gen-{kpId}-s{slot}`；面板淡入过渡。
- **2026-07-17 晚**：放大宝石胶囊与地图宝石尺寸，提升可点击性与可见度。

### 10. 个性化资源模块精简

- 移除小游戏、动画风格选项；聚焦多模态资源生成。
- `PedagogicalBundleViewer.vue` / `PersonalizedResourceContentViewer.vue`：折叠面板展示各模块。
- 生成内容经 `stripMarkdownAsterisks()` 净化，禁止 `*` 符号泄漏。

### 11. 成长档案与浅色模式

- `StudentGrowthView.vue`：统计卡玻璃 HUD、Explorer 资料卡角标、错题分析环形图 sci-fi 主题。
- 技能掌握度：7 大学域真实名称 + 霓虹进度条，减少底部留白。
- `plex-theme.css`：星轨/试炼页浅色模式对比度与卡片层次优化。

### 12. UI 科技风增强（非星轨）

- `StudentControlView`、`MessengerView`、`PlexPieChart`（sci-fi prop）等组件霓虹/扫描线/HUD 装饰。
- 试炼页移除「查看星图」按钮。

## 新增 / 关键文件索引

```
frontend/src/
  components/discovery/StarMapParticles.vue
  components/starpath/StarPathTrackCanvas.vue
  components/trial/QuestionSlotGems.vue
  composables/useMapViewport.ts
  constants/starPathUnlock.ts
  utils/
    explorationNarrative.ts
    questionNaming.ts
    questionStemSanitizer.ts
    starPathProgress.ts
    starPathTrackLayout.ts
    practiceQuestionCache.ts

backend/
  app/constants/star_path_unlock.py
  app/services/practice_question.py
  scripts/audit_practice_questions.py
  tests/test_practice_questions.py
```

## 新增依赖

| 包 | 用途 |
|----|------|
| `@dagrejs/dagre` | 星轨地图节点自动布局 |

粒子效果、地图视口、题干净化均为原生实现，未引入 tsparticles 等重型库。

## 验证结果

| 检查项 | 结果 |
|--------|------|
| 前端 `npm run build` | 通过（含 vue-tsc） |
| 后端 mistakes / student_progress / learning_path 测试 | 9/9 通过 |
| 后端 practice_questions 测试 | 通过 |
| 编辑文件 lint | 无新增错误 |

## 遗留与后续建议

1. **星轨页内嵌编辑器**：当前切换小题会跳转路由；如需不离开地图的内联练习，可增 inline practice 模式。
2. **API 导入题叙事**：外部题库经 `wrapExploration` 包装，复杂算法题可继续扩充 `SEMANTIC_TITLE_RULES`。
3. **个性化资源生成质量**：已去动画/小游戏，多模态内容质量仍依赖 LLM 与审核链路。
4. **地图美学**：dagre 默认横向链已可用；域内节点较多时可考虑 elkjs 或手工坐标表微调。

## 分支信息

- 当前分支：`codex/multi-ai-assistents`
- 文档日期：2026-07-17
