# AI / Agent 用 Python 库（本机可选栈）

**性质**：与 `backend/requirements.txt`（Flask 生产依赖）**分离**，记录开发机上为 **LangGraph、RAG、沙箱 Agent** 等任务准备的 Python 包。新会话里若用户任务明显匹配下表某一列，可**直接选用对应库**编写脚本或工具，无需再问「是否已安装」——以本文档与 `pip show <包名>` 为准。

**最后核对**：以本机 `pip` 为准；下列版本为一次 `pip show` 的快照，升级后不必逐字同步本文，但请同步更新「已安装 / 未安装」状态说明。

---

## 一览

| PyPI / 导入名 | 当前状态 | 典型版本（快照） | 何时优先使用 |
|----------------|----------|------------------|--------------|
| **langgraph** | 已安装 | 1.2.0 | 多步状态机、Agent 图、检查点恢复、与 LangChain 生态编排 |
| **e2b** | 已安装 | 2.21.0 | 云端隔离沙箱里跑代码/命令、给 Agent 安全执行环境（需 [E2B](https://e2b.dev) API Key） |
| **llama-index**（含 **llama-index-core**） | 已安装 | 0.14.21 | 文档索引、RAG、查询引擎、与多种 LLM/嵌入对接 |
| **crewai** | **已安装**（`backend/.venv-crewai`，Python 3.12，v1.14.6） | 1.14.6 | 多 Agent 角色分工、Crew 编排；Flask 3.14 进程会通过 `.venv-crewai` 自动加载 |

---

## 各库说明与调用提示

### LangGraph

- **导入**：`from langgraph.graph import StateGraph` 等（以 [官方文档](https://docs.langchain.com/oss/python/langgraph/overview) 为准）。
- **适用**：有环/分支的 Agent 流程、人机协同中断、持久化 checkpoint。

### E2B

- **导入**：`from e2b import Sandbox` 等（以当前 SDK 文档为准）。
- **适用**：不信任模型生成代码时的隔离执行、教学场景「学生代码沙箱」原型。
- **注意**：需环境变量或配置中的 **E2B API Key**，勿写入仓库。

### LlamaIndex

- **导入**：`from llama_index.core import VectorStoreIndex` 等；元包 `llama-index` 会拉齐常用子包（如 `llama-index-llms-openai`）。
- **适用**：PDF/Markdown 切块、向量检索、与项目文档（如 `backend_api_design.md`）结合的问答原型。

### CrewAI（已安装于 `backend/.venv-crewai`）

- **仓库**：https://github.com/crewAIInc/crewAI  
- **安装**（需 Python 3.10–3.12，**不支持 3.14**）：

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File scripts/install_crewai.ps1
```

或手动：

```bash
py -3.12 -m venv .venv-crewai
.venv-crewai\Scripts\pip install "git+https://github.com/crewAIInc/crewAI.git@5cdc420c50cf9cb9ca12b50fdba3125377743a53#subdirectory=lib/crewai"
```

- **启用**：环境变量 `AGENT_BACKEND=auto`（默认，检测到 venv 即报 `crewai`）或 `crewai`；真实 LLM 推理需配置 `OPENAI_API_KEY`（无 Key 时仍走 Mock fallback）。
- **注意**：不要直接 `pip install` 仓库根目录（会装成 `UNKNOWN`）；必须带 `#subdirectory=lib/crewai`。

---

## 与后端工程的关系

- **不要**把上述库默认写进 `backend/requirements.txt`，以免扩大生产镜像、引入与 Flask 栈无关的冲突（例如不同版本的 `langchain-core`）。
- 若将来要把 RAG/Agent **并入** 后端服务，应单独开 issue：锁定版本、子进程/队列隔离、密钥与配额。

---

## 维护

新增或卸载任一类「Agent 常用 Python 库」时，请更新本文件，并在 [AGENTS.md](../AGENTS.md) 中若引用了本清单，核对链接仍有效。
