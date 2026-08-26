# PLEX AI 使用报告：API 调用与开源项目说明

## 一、总体结论

本系统的 AI 能力采用「**开源编排层 + OpenAI 兼容 HTTP 调用 + 多供应商降级**」结构：

1. **大模型推理** 通过开源 HTTP 客户端调用 DeepSeek、OpenAI、OpenRouter、讯飞星火等 **OpenAI Chat Completions 兼容接口**。
2. **多智能体编排** 引入开源框架 **CrewAI**、**LangGraph**。
3. **多模态** 使用开源 **websocket-client** 接入讯飞 TTS；图像与视频走火山方舟 Ark HTTP API。

---

## 二、外部 API 清单

| 服务 | 协议/形态 | 主要用途 | 配置入口（环境变量） |
|---|---|---|---|
| **DeepSeek** | HTTPS，OpenAI 兼容 `/v1/chat/completions` | 驿站答疑（优先）、学习路径建议、补给站解析、试炼辅导、资源生成主通道 | `DEEPSEEK_*`、`DEEPSEEK_MESSENGER_API_KEY`、`DEEPSEEK_LEARNING_PATH_API_KEY` 等 |
| **OpenAI** | HTTPS，Chat Completions | 多智能体角色增强、资源质量审核、部分流水线步骤 | `OPENAI_API_KEY`、按角色拆分的 `OPENAI_*_API_KEY` |
| **OpenRouter** | HTTPS，兼容接口 | DeepSeek 不可用时的 LLM 备选 | `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` |
| **讯飞星火 Spark Lite** | HTTPS，星火 Open 兼容接口 | 画像抽取、资源生成兜底、试炼代码提示、补给站兜底 | `IFLYTEK_SPARK_*` |
| **讯飞星辰 Agent（小E）** | HTTPS，工作流 Chat Completions | 驿站自由问答可选上游 | `XFYUN_AGENT_*` |
| **讯飞在线 TTS** | WSS `tts-api.xfyun.cn` | 个性化资源「语音讲解」合成 MP3 | `IFLYTEK_TTS_*` |
| **火山方舟 Ark** | HTTPS `/api/v3` | 答疑图解（Seedream 图像） | `ARK_API_KEY`、`ARK_IMAGE_MODEL`、`ARK_VIDEO_MODEL` |

**降级策略（共性）**：外呼失败或未配置时，返回 `local_rules` / Mock / 规则文案，并在任务元数据中记录实际 `backend`，避免把本地兜底伪装成真实模型结果。

---

## 三、调用 API 时引入的开源项目

### 3.1 HTTP / TLS / 流式通信

| 开源项目 | 许可证（常见） | 引入位置 | 怎么用 |
|---|---|---|---|
| **[requests](https://github.com/psf/requests)** | Apache-2.0 | `backend/requirements.txt`；`agents/http_client.py`、`agents/llm_client.py`、`iflytek_spark.py`、`ark_media.py`、`code_execution.py` 等 | 对 DeepSeek / OpenAI / OpenRouter / 星火 / Ark / Judge0 发起 POST/GET；统一超时、JSON 载荷、Bearer 鉴权 |
| **[truststore](https://github.com/sethmlarson/truststore)** | MIT | `requirements.txt`；在 `http_client` 中于创建 Session 前 `inject_into_ssl()` | 复用操作系统证书库，解决本机代理 TLS 中间人导致的 SSL 校验失败 |
| **[websocket-client](https://github.com/websocket-client/websocket-client)** | Apache-2.0 | `requirements.txt`；`app/services/tts_service.py` | 连接讯飞 TTS WebSocket，流式收取音频帧并拼成 MP3 |
| **[python-dotenv](https://github.com/theskumar/python-dotenv)** | BSD-3-Clause | `requirements.txt` | 加载后端 `.env` 中的 API Key / Base URL，供运行时读取 |

**自研封装（调用入口）**：

- `backend/agents/http_client.py`：代理感知的 `direct_post` / `direct_get`（支持 `LLM_HTTP_PROXY`、系统代理、localhost 直连）。
- `backend/agents/llm_client.py`：统一 `llm_provider` / `messenger_provider` / `learning_path_provider` / `chat_json` / `chat_text`，按场景选择 DeepSeek 或 OpenAI 兼容端点。
- `backend/app/services/llm_stream.py`：SSE/流式增量输出（画像对话、驿站流式答疑）。

### 3.2 语音合成相关开源

| 开源项目 | 引入位置 | 怎么用 |
|---|---|---|
| **[edge-tts](https://github.com/rany2/edge-tts)** | `requirements.txt`；`TtsService` 第二优先级 | 讯飞 TTS 失败时，用 Edge 在线语音合成讲解音频，落盘到 `MEDIA_ROOT/audio` |
| **[pyttsx3](https://github.com/nateshmbhat/pyttsx3)** | `requirements.txt`；`LocalTtsService` | 外网不可用时的 Windows SAPI 离线兜底 |

统一入口：`TtsService.synthesize_to_media` → **讯飞 → Edge → 本地**。

### 3.3 多智能体 / Agent 编排开源

| 开源项目 | 引入位置 | 怎么用 |
|---|---|---|
| **[CrewAI](https://github.com/crewAIInc/crewAI)** | `requirements-agents.txt`（Git 固定提交）；独立虚拟环境 `backend/.venv-crewai` | `AGENT_BACKEND=auto|crewai` 时，用 `Agent/Crew/Task` 编排学生诊断、路径规划等；真实推理仍依赖 `OPENAI_API_KEY` 或 `OPENROUTER_API_KEY`；不可用则回退自研顺序流水线 |
| **[LangGraph](https://github.com/langchain-ai/langgraph)** | 可选本机 Agent 栈（见 `docs/AI-Agent-Python栈.md`）；`agents/graphs/learning_path_graph.py` | 将学习路径规划建成状态图（上下文加载 → 诊断 → 规划 → 理由）；未安装时顺序执行同等步骤 |
| **[LlamaIndex](https://github.com/run-llama/llama_index)** | 可选；`app/services/rag_service.py`（`RAG_BACKEND=llamaindex`） | 读取 `backend/data/rag_docs`，建本地向量索引并查询，为驿站等场景提供 RAG 上下文；默认 `mock` 关键词库 |
| **[E2B Python SDK](https://github.com/e2b-dev/E2B)** | 可选；`app/services/code_execution.py` | `CODE_EXECUTION_BACKEND=e2b` 时在云沙箱执行学生代码，隔离不可信代码 |

### 3.4 知识图谱 / 结构化校验 / Web 框架（支撑 AI 业务 API）

| 开源项目 | 引入位置 | 怎么用 |
|---|---|---|
| **[neo4j](https://github.com/neo4j/neo4j-python-driver)**（Python Driver） | `requirements.txt`；`neo4j_client.py` | 可选图数据库后端；未配置时用内存图，支撑星轨路径与知识关联查询 |
| **[jsonschema](https://github.com/python-jsonschema/jsonschema)** | `requirements.txt`；个性化资源生成 | 校验 LLM 生成的资源 JSON/Markdown 是否符合约定 Schema，不合格则拒绝或重试 |
| **[pydantic](https://github.com/pydantic/pydantic)** | `requirements.txt` | 智能体诊断/契约侧结构化数据建模 |
| **[Flask](https://github.com/pallets/flask)** + **Flask-JWT-Extended** + **Flask-CORS** + **Flask-SQLAlchemy** | `requirements.txt` | 对外 REST/SSE API 服务端；鉴权后由服务层再调用外部 AI API |
| **[Alembic](https://github.com/sqlalchemy/alembic)** / **SQLAlchemy**（经 Flask-SQLAlchemy） | 生产栈 | 持久化画像版本、资源任务、审核状态、AI `backend`/`model` 元数据 |

---

## 四、按业务场景的使用方式

### 4.1 驿站助手（小E）答疑

| 步骤 | 开源/组件 | 行为 |
|---|---|---|
| 路由与提示词 | 自研 `messenger_chat.py` | 概念题优先 DeepSeek；低质反问熔断后换通道；可叠 RAG 上下文 |
| HTTP 调用 | `requests` + `http_client` + `llm_client.messenger_provider` | `POST .../chat/completions` |
| 可选上游 | 讯飞星辰 Agent / 星火 | `xfyun_agent.py` / `iflytek_spark.py` |
| 流式 | `llm_stream.iter_openai_stream` | 前端 SSE 展示 `stage` / `delta` |
| 知识增强 | LlamaIndex（可选）或 Mock RAG | `RagService.build_context` |

### 4.2 对话式学生画像

| 步骤 | 开源/组件 | 行为 |
|---|---|---|
| 流式生成 | Flask SSE + OpenAI 兼容流式接口 | `student_profile` 路由 + `iter_openai_stream` |
| 结构化抽取 | 星火 `chat_json` 或 LLM | 写入多维画像（≥6 维，验收实测 9 维） |
| 降级 | 本地规则 | `backend: local_rules` |

### 4.3 个性化资源生成（多智能体流水线）

| 角色（逻辑） | 典型后端 | 开源支撑 |
|---|---|---|
| 画像解释 / 知识检索 / 教学设计 / 路径规划 | OpenAI（按角色独立 Key）或 DeepSeek | `llm_client.openai_agent_provider`、`requests` |
| 资源正文生成 | DeepSeek → OpenAI/OpenRouter → 星火 | `personalized_resource.py` |
| 质量审核 | OpenAI / CrewAI notes | `jsonschema` 校验 + 审核智能体 |
| 语音讲解 | 讯飞 TTS / edge-tts / pyttsx3 | `tts_service.py` + `websocket-client` |
| 视频课 | Ark 视频任务（可选） | `ark_media.py`；未配置则返回分镜脚本 |
| 编排可选增强 | CrewAI | `.venv-crewai` 子进程 |

### 4.4 学习路径 AI 建议

- 接口：`POST /api/v1/student/learning-path/advice`
- 调用：`learning_path_provider()` → DeepSeek Chat Completions（`requests`）
- 图规划可选：`LangGraph` 状态机（`learning_path_graph.py`）
- 失败：本地掌握度规则文案

### 4.5 试炼辅导 / 补给站 / 教师 AI 出题

- 优先 DeepSeek JSON/文本补全；星火作超时或未配置时的兜底
- 代码执行：Judge0 / E2B / 本地 Mock（`code_execution.py` + `requests` 或 `e2b` SDK）

### 4.6 答疑图解 / 多模态卡片

- Ark `images/generations`（Seedream）经 `requests` 拉图并缓存到 `MEDIA_ROOT`
- 前端用 Markdown / 媒体 URL 展示，不直连 Ark Key

---

## 五、前端侧：消费 AI API 结果时用到的开源项目

前端**不直接持有**大模型密钥，只调用本项目后端 API；下列开源库用于展示与交互 AI 产出：

| 开源项目 | 怎么用 |
|---|---|
| **[axios](https://github.com/axios/axios)** | 调用 `/api/v1` REST；携带 JWT |
| **[Vue 3](https://github.com/vuejs/core) / [Vite](https://github.com/vitejs/vite) / [Pinia](https://github.com/vuejs/pinia) / [Vue Router](https://github.com/vuejs/router)** | 学生/教师端页面与状态 |
| **[Naive UI](https://github.com/tusen-ai/naive-ui)** | 对话、审核、资源卡片等 UI |
| **[markdown-it](https://github.com/markdown-it/markdown-it)** + **[highlight.js](https://github.com/highlightjs/highlight.js)** + **[KaTeX](https://github.com/KaTeX/KaTeX)**（`@vscode/markdown-it-katex`） | 渲染驿站/资源中的 Markdown、代码高亮、公式 |
| **[mermaid](https://github.com/mermaid-js/mermaid)** | 渲染 AI/资源中的流程图类内容 |
| **[ECharts](https://github.com/apache/echarts) + [vue-echarts](https://github.com/ecomfe/vue-echarts)** | 画像雷达、学习趋势等可视化 |
| **[AntV G6](https://github.com/antvis/G6)** | 知识图谱可视化 |
| **[Vue Flow](https://github.com/bcakmakoglu/vue-flow)** | 多智能体编排流程图展示 |
| **[@guolao/vue-monaco-editor](https://github.com/imguolao/vue-monaco-editor)**（Monaco） | 试炼编程编辑器，配合判题 API |
| **[Uppy](https://github.com/transloadit/uppy)** | 知识库/资源相关上传（对接后端） |
| **[Fuse.js](https://github.com/krisk/fuse)** | 前端模糊检索辅助 |
| **[Driver.js](https://github.com/kamranahmedse/driver.js)** | 引导式产品演示 |

---

## 六、调用链路简图

```text
[前端 Vue/Axios/SSE]
        │  JWT + /api/v1
        ▼
[Flask 业务 API]
        │
        ├─► llm_client / http_client (requests + truststore)
        │       ├─ DeepSeek / OpenAI / OpenRouter
        │       └─ 讯飞星火 / 星辰 Agent（兼容 Chat Completions）
        │
        ├─► tts_service
        │       ├─ websocket-client → 讯飞 TTS
        │       ├─ edge-tts
        │       └─ pyttsx3
        │
        ├─► ark_media (requests) → 火山方舟 图/视频
        │
        ├─► crew.py / LangGraph / LlamaIndex
        │
        └─► code_execution → Judge0(requests) / E2B / Mock
```
