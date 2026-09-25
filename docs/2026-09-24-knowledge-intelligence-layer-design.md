# PLEX Knowledge Intelligence Layer（Graph-enhanced RAG）架构分析与设计

**日期**：2026-09-24
**范围**：在现有 PLEX Universe（Flask + Vue3）基础上新增「知识图谱 + 向量知识库 + 个性化 RAG + 学习者画像」融合的公共知识服务，供小 E、学习诊断、路径规划、资源生成、教师干预共同调用。

---

## 1. 现有工程目录与架构分析

```
zhongruan/
├── backend/                       Flask 2.3 + Flask-SQLAlchemy 3 + Flask-JWT-Extended
│   ├── app/__init__.py            create_app：db.create_all + 轻量列迁移 + 种子
│   ├── app/config.py              Config/Development/Testing/Production；.env + .env.spark.local
│   ├── app/models/                SQLAlchemy 模型（BaseModel: id/created_at/updated_at）
│   ├── app/routes/                Blueprint，统一 /api/v1 前缀，success_response/error_response
│   ├── app/services/              业务服务（静态方法类为主）；子包先例 resource_audit/
│   ├── app/data/                  知识节点注册表、拓扑、课程知识 md 契约、智能体注册表
│   ├── app/utils/                 response / decorators(role_required) / db_migrate / time
│   ├── agents/                    运行时多智能体（诊断/图谱/路径/反馈/教师助理/资源流水线）
│   ├── data/rag_docs/python-basics/  8 个模块 md，100 个知识点，含 document_id 契约字段
│   ├── migrations/versions/       Alembic 0001–0011
│   └── tests/                     unittest，create_app('testing') 内存 SQLite
└── frontend/src/                  Vue3 + Vite + Naive UI + Pinia + Axios
    ├── api/                       每域一个 ts 文件，http.ts 统一拦截 JWT/刷新
    ├── views/                     AdminHomeView（单页 4 个 nav）/ Teacher*/ Student*/ MessengerView
    ├── components/admin|teacher|agent|shared  PlexKnowledgeGraph(G6) 等
    ├── router/index.ts            三端路由隔离 + 角色守卫
    └── styles/plex-theme.css      CSS 变量单一来源（冷蓝/雾青、玻璃卡片）
```

运行环境：根目录 `.venv`（Python 3.12）已安装 chromadb 1.1.1、numpy、openai、pdfplumber、python-docx、python-pptx、markdown-it-py、onnxruntime；Docker 29 可用；MySQL 8 compose 已有。

## 2. 已有数据库模型（与本功能相关）

| 表 | 用途 | 复用方式 |
|---|---|---|
| `knowledge_nodes` (KnowledgeNode) | 100 个 Python 知识节点镜像（注册表 `knowledge_node_registry.py` 派生） | 新图谱 concept 节点 `concept_id == kg_id`，保证全站 ID 一致 |
| `problems` (Problem) | 统一题库，`kg_node_id` 已绑定知识节点 | 作为 Exercise 节点来源（EXERCISE_FOR） |
| `student_profiles` / `_history` / `_suggestions` / `_diagnostics` | 七维（+cognitive_state）学习者画像 | RAG 只读，不写 |
| `student_mistakes` | 错题（knowledge_key、error_type、SM-2） | 错误模式 / 薄弱知识 |
| `trial_question_progress` | 作答记录 | 掌握度证据（经 KnowledgeGraphService） |
| `learning_adaptations` | 知识点级干预 | 当前干预上下文 |
| `personalized_learning_resources` | AI 生成资源（review_status、citations） | 教师审核后可作为 teacher_verified 资源导入知识库 |
| `learning_resources` | 静态资源目录 | 平台已有资源导入 |

## 3. 已有 AI / Agent 模块

- `agents/llm_client.py`：OpenAI 兼容 `chat_json/chat_text`，按用途返回 provider（DeepSeek/OpenRouter/OpenAI/星火），测试环境自动禁外呼。
- `app/services/llm_stream.py`：SSE 流式与供应商链。
- `app/services/iflytek_spark.py`：星火 Lite 适配器。
- `app/services/messenger_chat.py`：小 E 驿站（DeepSeek→星火→星辰→规则/RAG 兜底），当前调用 `RagService._mock_query`。
- `app/services/rag_service.py`：**Mock** RAG（MOCK_DOCUMENTS/MOCK_QA），`/kb/*` 路由；LlamaIndex 分支未落地。
- `app/services/knowledge_graph.py` + `neo4j_client.py`：静态拓扑 + 学情状态（weak/learning/mastered），Neo4j 可选、内存回退。
- `app/services/learning_path.py`：前置检查、拓扑排序、NBA、掌握度 STATUS_TO_SCORE。
- `agents/knowledge_graph_agent.py`、`agents/knowledge_scope.py`：基于关键字硬编码前置表。
- `agents/resource_pipeline_agents.py::retrieve_knowledge`：读 `course_knowledge.knowledge_section()` 单节 md 原文。
- `agents/diagnosis/`：四层错因诊断引擎。
- `app/data/agent_registry.py`：智能体注册表（前端 PlexAgentFlow 对齐）。

## 4. 可复用的现有代码

| 复用点 | 用途 |
|---|---|
| `knowledge_node_registry`（100 节点、legacy key 映射、scope_names）| 概念节点种子、Query→concept 词典、knowledge_key 归一 |
| `kg_topology.KG_EDGES`（prerequisite/related/path 等）| 图谱边种子（映射为 PREREQUISITE_OF/RELATED_TO/NEXT_RECOMMENDED）|
| `course_knowledge._parse_sections/_section_fields` 与 rag_docs md | 首批文档导入 + Example/Misconception/Exercise 节点抽取 |
| `KnowledgeGraphService.get_student_graph` + `STATUS_TO_SCORE` | 学生知识掌握度 |
| `StudentProfileService.get_or_create` | 七维画像只读 |
| `MistakeService.list_weak_knowledge/list_recent_with_meta` | 薄弱点与错误模式 |
| `agents.llm_client` / `llm_stream` | LLMProvider 实现底座（不绑定供应商）|
| `file_upload.validate_and_save` 场景 `knowledge-doc`/`course-material` | 文件落盘与签名校验 |
| `CourseSafetyService` | 查询安全 |
| `role_required` / `success_response` | 路由规范 |
| `PlexKnowledgeGraph.vue`（G6）| 教师端/管理端图谱可视化 |
| `PlexFileUploader` + `ADMIN_PRESETS.knowledgeDoc` | 管理端上传组件 |
| `MessengerView` SSE done 事件、`PlexAgentTracePanel` | 学生端小 E 展示参考知识 |

## 5. 新增目录与文件

```
backend/app/models/knowledge_graph.py       KnowledgeConcept, KnowledgeRelation
backend/app/models/knowledge_document.py    KnowledgeDocument, KnowledgeChunk, KnowledgeIndexJob
backend/app/models/rag_query_log.py         RagQueryLog
backend/app/services/knowledge/             ← Knowledge Intelligence Layer（子包，沿 resource_audit 先例）
    __init__.py
    settings.py                              JSON 配置加载（权重/阈值/Prompt）+ 环境变量覆盖
    config/retrieval.json  strategy.json  prompts.json
    schemas.py                               QueryUnderstanding / LearnerContext / RetrievedChunk / RagAnswer
    providers/embedding.py                   EmbeddingProvider（OpenAI 兼容 / 本地哈希回退）
    providers/vector_store.py                VectorStore（Chroma / 本地 numpy JSONL 回退）
    providers/llm.py                         LLMProvider（封装 agents.llm_client）
    graph_service.py                         图谱 CRUD、k-hop 扩展、种子
    parser_service.py                        md/txt/pdf/docx/pptx 解析
    chunk_service.py                         教育语义切分 + metadata + 概念映射
    embedding_service.py  vector_service.py  index_service.py（异步索引状态机）
    lexical_index.py                         BM25 词法检索（Hybrid）
    retrieval_service.py                     Query Understanding + Graph + Vector + Filter
    rerank_service.py                        加权重排（配置化）
    learner_context_service.py               画像/掌握度/错题/当前任务 只读聚合
    strategy_service.py                      Educational Strategy + Hint Level Policy
    context_builder.py                       learner/knowledge/retrieved/teaching 四类上下文
    rag_service.py                           完整流水线 + 日志 + 可信度
    knowledge_service.py                     Agent 公共门面（Agent 不直接碰向量库）
    analytics_service.py                     高频检索/薄弱点统计（教师端）
backend/app/routes/knowledge.py             /api/v1/knowledge/*
backend/app/routes/rag.py                   /api/v1/rag/*
backend/migrations/versions/20260924_0012_knowledge_intelligence.py
backend/tests/test_knowledge_layer.py
frontend/src/api/knowledge.ts  rag.ts
frontend/src/components/admin/AdminKnowledgeBasePanel.vue   知识库/图谱/索引/Chunk
frontend/src/components/admin/AdminRagDebugPanel.vue        RAG 调试
frontend/src/views/TeacherKnowledgeView.vue                 教师知识星域
frontend/src/components/student/XiaoEKnowledgeCard.vue      学生端简化引用卡片
```

## 6. Knowledge Graph 数据模型

`knowledge_concepts`（多类型节点，`node_type` 区分）：
`concept_id(PK) name description course_id chapter node_type[concept|skill|example|exercise|misconception|resource|objective] difficulty(1-5) importance(0-1) learning_objectives(JSON) common_misconceptions(JSON) tags(JSON) mastery_threshold embedding_text source status kg_node_id ref_type ref_id created_at updated_at`

`knowledge_relations`：`source_id target_id relation_type[PREREQUISITE_OF|RELATED_TO|PART_OF|EXAMPLE_OF|EXERCISE_FOR|MISCONCEPTION_OF|REMEDIATES|NEXT_RECOMMENDED] weight source teacher_verified verified_by note`，唯一键 (source,target,type)，允许多前置。

对外 `concept.to_dict(expand=True)` 派生 `prerequisites / related_concepts / example_ids / exercise_ids / resource_ids / misconception_ids / next_recommended`。

## 7. Vector DB 技术选择

**选型：ChromaDB（PersistentClient 本地嵌入式）为默认实现，本地 numpy 向量存储为零依赖回退；统一 `VectorStore` 接口可替换。**

原因：
- `.venv` 已安装 chromadb 1.1.1，无需新增基础设施；PersistentClient 单文件目录、Windows 友好、无独立进程；后续可切 `chromadb server` Docker 或 Qdrant/Milvus，只换实现类。
- 教学演示数据量（万级 chunk）内存/SQLite 后端足够；metadata where 过滤满足 course/concept/difficulty/teacher_verified 过滤需求。
- 不选 Neo4j 向量索引/Milvus/ES：过重；不选 LlamaIndex：与现有 provider 抽象重复且依赖大。
- Embedding：`EmbeddingProvider` 抽象，`OpenAICompatibleEmbeddingProvider`（`EMBEDDING_API_KEY/BASE_URL/MODEL`，兼容 OpenAI / 阿里百炼 text-embedding-v3 / SiliconFlow / Ollama）；未配置 Key 时用 `LocalHashEmbeddingProvider`（字符 n-gram 哈希投影，确定性、离线可跑、单测稳定），并叠加 BM25 词法检索形成 Hybrid，保证无外网也是真实检索而非 Mock。

## 8. RAG 完整数据流

```
POST /rag/query {query, context:{task_type, question_id, concept_hint, hint_level}}
 → CourseSafety
 → LearnerContextService.build(user_id)        画像维度 / 节点掌握度 / 薄弱点 / 近期错题 / 当前任务
 → RetrievalService.understand(query, learner)  意图 / 概念候选(词典+图谱+可选LLM) / 问题类型 / 难度需求
 → GraphService.expand(concepts, hops=1..2)     前置(未掌握优先) / 相关 / 迷思 / 后续
 → VectorService.search(query+concept terms, filters) ∪ LexicalIndex.search  → 候选 Top-K
 → MetadataFilter(course, concept_ids, difficulty band, resource_type, teacher_verified)
 → RerankService.score = Σ w_i·f_i（retrieval.json 权重）
 → StrategyService.select(mastery, intent, error_type, task) + HintPolicy
 → ContextBuilder → learner_context / knowledge_context / retrieved_context / teaching_strategy
 → LLMProvider.generate(prompt from prompts.json)  |  无 LLM → 抽取式 grounded 回答
 → 置信度评估 → LOW_CONFIDENCE → knowledge_grounded=false
 → RagQueryLog（脱敏 query 预览）
 → {answer, concepts, sources, confidence, teaching_strategy, hint_level, recommended_next, knowledge_grounded, debug?}
```

学习行为记录与画像更新仍由现有 Diagnosis Agent / StudentProfileService 完成，RAG 只产生 `RagQueryLog` 作为学习证据，不写画像。

## 9. 新增 / 修改 API

新增（均 `/api/v1`，JWT，统一响应）：

| 方法 | 路径 | 角色 |
|---|---|---|
| POST | /knowledge/documents | teacher/admin（multipart 或 JSON 注册已上传文件）|
| POST | /knowledge/documents/{id}/index | teacher/admin |
| GET | /knowledge/documents | teacher/admin |
| GET | /knowledge/documents/{id} | teacher/admin（含 chunks 分页）|
| DELETE | /knowledge/documents/{id} | admin |
| PATCH | /knowledge/documents/{id}/verify | teacher/admin |
| GET | /knowledge/documents/{id}/chunks | teacher/admin |
| GET | /knowledge/graph | 全部登录用户（学生只读）|
| GET | /knowledge/concepts/{id} | 全部 |
| POST/DELETE | /knowledge/relations | teacher/admin |
| GET | /knowledge/index/status | teacher/admin |
| POST | /knowledge/seed | admin（种子/重建）|
| GET | /knowledge/analytics/queries | teacher/admin |
| POST | /rag/query | 全部 |
| POST | /rag/retrieve | teacher/admin |
| GET | /rag/sources/{chunk_id} | 全部（学生仅可见已 READY 文档片段）|
| GET | /rag/logs | admin |

修改：`/kb/query`、`/kb/status`、`/kb/documents` 内部委托到新 KnowledgeService（保持返回结构兼容）；`/student/messenger/chat(/stream)` done 事件新增 `knowledge` 字段。

## 10. 预计修改的现有页面

- `AdminHomeView.vue`：新增 nav `knowledge`「知识底座 Knowledge Nexus」，挂载 `AdminKnowledgeBasePanel` + `AdminRagDebugPanel`。
- `TeacherSidebar.vue` / `router` / `useTeacherShellChrome`：新增 `/teacher/knowledge` 知识星域页。
- `MessengerView.vue`：在小 E 回复下方展示「参考知识 / 相关知识点 / 推荐下一步 / 参考来源」简化卡片。
- `TrialAiFloatingBall.vue`：练习场景传递 `task_type=trial` 与 hint_level，接入 Answer Policy。
- `messenger_chat.py`、`knowledge_graph_agent.py`、`resource_pipeline_agents.retrieve_knowledge`、`learning_path.ai_advice`：改为经 `KnowledgeService` 获取 grounded 知识。
- `.env.example`、`README.md`、`AGENTS.md`、`backend_api_design.md`：补充配置与接口说明。
