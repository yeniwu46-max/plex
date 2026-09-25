# 2026-09-25 PLEX 技术更新：知识智能层与学生/管理端体验

> 承接 Graph-enhanced RAG（Knowledge Intelligence Layer）后端落地与多轮学生端体验迭代。架构设计见 [2026-09-24-knowledge-intelligence-layer-design.md](./2026-09-24-knowledge-intelligence-layer-design.md)。

## 总览

| 模块 | 要点 |
|------|------|
| **Knowledge Intelligence Layer** | 后端完整链路 + 管理/教师/学生消费面；向量库与 MySQL 分离；Agent 经 `KnowledgeService` 取材 |
| **管理端** | 「知识智能」：文档索引、知识星域、检索诊断、使用分析 |
| **教师端** | `/teacher/knowledge` 知识星域、资源审核、关联修正、学情分析 |
| **学生端·小E** | 参考知识卡片、多会话 BOX、Mermaid 全图弹窗、语音输入修复 |
| **学生端·试炼** | 教练上下文同步、Hint 策略、知识卡片裁剪、语音共用 |
| **星轨** | 节点间距与像素布局、点击切换与 URL 同步、视口居中动画 |
| **资源** | 可学习资源 / 已生成资源：搜索、日期、知识主题筛选 |
| **成长档案** | SM-2 错题复习改为客观问卷计分；教师共享 PDF 预览修复 |
| **主题** | 浅色模式补充驿站、成长档案、文件交换等全局覆盖 |

---

## 一、Knowledge Intelligence Layer（后端）

### 架构约束（与 PRD 一致）

- Vector DB 与业务元数据分离，以 `concept_id` / `chunk_id` 关联。
- 检索不直接修改学习者画像；练习场景 Hint Level 1–4 进入 Answer Policy。
- 证据不足返回 `LOW_CONFIDENCE`，`knowledge_grounded=false`。
- Agent **不得**直接操作 Vector DB；统一 `KnowledgeService` / `KnowledgeRagService`。

### 主要包与 API

- 包路径：`backend/app/services/knowledge/`（settings、retrieval、rerank、graph、index、rag、analytics 等）。
- 路由：`/api/v1/knowledge/*`（文档、图谱、概念、关系、索引状态、分析）、`/api/v1/rag/*`（query、retrieve、sources、logs）。
- 模型与迁移：`knowledge_document`、`knowledge_graph`、`rag_query_log` 等；Chroma 默认向量库。
- 启动：`KnowledgeService.bootstrap_async` 后台 recover + ensure_ready + vector repair。
- 测试：`backend/tests/test_knowledge_layer.py`（15 项）。

### 集成点

- 小E 流式/非流式：`messenger_chat.py` 两段式 prepare/finalize，done 事件带 `knowledge` 安全视图。
- 试炼教练：`trial_coach_agents.py` 经 `KnowledgeService.prepare` + Answer Policy + 学生安全 `knowledge` 视图。
- 资源流水线、知识图谱 Agent、学习路径：`KnowledgeService` 辅助方法。

### 配置

- `backend/.env.example` 增加 `EMBEDDING_*`、`VECTOR_*`、`KNOWLEDGE_*`、`RAG_LLM_*`。
- 权重与策略：`config/retrieval.json`、`config/strategy.json`（含 hint `max_code_lines` 等）。

---

## 二、管理端与教师端（前端）

### 管理端 · 知识智能

- `AdminHomeView` 导航项「知识智能」。
- `AdminKnowledgePanel.vue`：文档上传/索引轮询、Chunk 查看、知识星域（PlexKnowledgeGraph）、使用分析。
- `AdminRagDebugPanel.vue`：检索测试、Rerank/Context/Answer 诊断（仅管理员可见分值）。
- API：`frontend/src/api/knowledge.ts`、`rag.ts`；`utils/knowledgeGraphMap.ts`。

### 教师端 · 知识星域

- 路由 `/teacher/knowledge`，`TeacherKnowledgeView.vue`。
- 图谱、AI 使用资源审核、关系修正、高频问题与薄弱点（analytics）。

---

## 三、学生端 · 驿站小E

| 能力 | 实现要点 |
|------|----------|
| 参考知识卡片 | `MessengerKnowledgeCard.vue`；流式 done 的 `knowledge` 字段 |
| 多会话 | `useMessengerChatSessions.ts`，localStorage 最多 5 窗；UI 折叠为 **BOX** |
| 知识图 | 对话内紧凑预览 → 点击 `MermaidDiagramModal` 全屏缩放/平移/保存 PNG |
| 语音 | `useSpeechRecognitionInput.ts` 共用；final/interim 重建文本，避免重复拼接 |
| 浅色 | `plex-theme.css` 下 `[data-theme='light']` 覆盖对话区、prompt-dock、BOX |

---

## 四、学生端 · 试炼浮球

- 每次提问 `buildPayload(props.context)` 携带最新代码与用例结果。
- 开场不再强推 `next_trial`；`trimTrialCoachKnowledge` + 后端 `_trial_student_knowledge_view` 裁剪推荐。
- Hint Level 与 Answer Policy 一致；语音与驿站同一 composable。

---

## 五、星轨（Star Path）

| 迭代 | 内容 |
|------|------|
| 布局 | `starPathTrackLayout.ts` 像素坐标 + 加大 `ranksep`/`nodesep`；轨道可横向拖拽 |
| 居中 | `useMapViewport`：`animatePanTo` / `centerOnElement` |
| 点击切换 | 节点 `@pointerdown.stop`；与画布拖拽分离；`StarPathLabView` 同步 `?domain=&kp=`，保留合法选中不强制回首节点 |

---

## 六、个性化资源与成长档案

### 资源筛选

- `resourceListFilters.ts`：标题模糊（fuse）、近 7/30/90 天、知识主题（MODULE_CATEGORY 粗分）。
- `StudentResourcesView.vue`：「可学习资源」弹窗高度缩短；「已生成资源」列表同套筛选。

### SM-2 错题复习

- `MistakeReviewQuestionnaire.vue` + `sm2ReviewQuestionnaire.ts`：5 道客观题（不清楚/部分/清楚）→ 换算 0–5 → 提交。
- 后端 `mistake.py` / `student_progress.py` 支持 `questionnaire_answers`；`test_mistakes.py` 扩展。

### 教师共享 PDF

- `classFiles.ts`：`fetchUploadPdfBlob`（JWT + `%PDF` 校验）。
- `ClassFileExchangePanel.vue`：`object` + iframe 回退，错误 toast 替代空白 PDF 框。

---

## 七、构建与验证

```bash
# 后端（testing）
cd backend
python -m unittest tests.test_knowledge_layer tests.test_trial_coach_agents tests.test_mistakes

# 前端
cd frontend
npx vue-tsc -b
npm run build   # 含 verify-production-copy
```

### 建议冒烟路径

1. 管理员 → 知识智能 → 索引状态 / 检索诊断。  
2. 教师 → 知识星域 → 审核资源、看薄弱点。  
3. 学生 → 驿站 → 提问 → 参考知识卡片 → 知识图全屏。  
4. 学生 → 试炼浮球 → 改代码后提问 + 语音。  
5. 学生 → 星轨 → 点击不同节点居中。  
6. 学生 → 成长档案 → PDF 预览 + 错题问卷复习。  
7. 全局切换浅色 → 驿站 / 成长档案 / 文件区可读。

---

## 八、主要新增/变更文件索引

### 后端（节选）

- `app/services/knowledge/**`、`app/routes/knowledge.py`、`app/routes/rag.py`
- `app/models/knowledge_*.py`、`app/models/rag_query_log.py`
- `agents/trial_coach_agents.py`、`app/services/messenger_chat.py`、`app/services/mistake.py`
- `tests/test_knowledge_layer.py`、`tests/test_mistakes.py`

### 前端（节选）

- `api/knowledge.ts`、`api/rag.ts`
- `components/admin/AdminKnowledgePanel.vue`、`AdminRagDebugPanel.vue`
- `components/common/MermaidDiagramModal.vue`、`MarkdownRenderer.vue`
- `components/growth/MistakeReviewQuestionnaire.vue`
- `components/student/MessengerKnowledgeCard.vue`、`ClassFileExchangePanel.vue`
- `components/starpath/StarPathTrackCanvas.vue`
- `composables/useMessengerChatSessions.ts`、`useSpeechRecognitionInput.ts`、`useMapViewport.ts`
- `views/MessengerView.vue`、`StarPathLabView.vue`、`StudentResourcesView.vue`、`StudentGrowthView.vue`、`TeacherKnowledgeView.vue`
- `styles/plex-theme.css`

### 文档

- `docs/2026-09-24-knowledge-intelligence-layer-design.md`
- 本文档

---

## 九、已知限制与后续建议

- 语音识别依赖浏览器 Web Speech API，非所有环境可用。
- 知识图 Mermaid 复杂图在低端设备上弹窗渲染可能略慢，可后续考虑服务端静态图缓存。
- 浅色模式已覆盖主路径；若个别子页面仍有硬编码深色，可按页面继续替换为 `--plex-*` 变量。
