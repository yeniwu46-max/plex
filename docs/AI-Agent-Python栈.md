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
| **crewai** | **未安装**（见下） | — | 多 Agent 角色分工、Crew 编排、YAML 任务流 |

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

### CrewAI（当前环境未装上）

在本机 **Python 3.14（Windows）** 上，`pip install crewai` 目前只会解析到 **0.11.2** 等旧约束，依赖需 **编译** 的 `regex` / `tiktoken` 旧版本，易与 **无预编译 wheel** 或 **缺少 Rust** 冲突而失败；从 **GitHub 源码** 安装若网络不稳定可能长时间卡在 `git clone`。

**建议**（任选其一）：

1. 使用 **Python 3.11 或 3.12** 新建虚拟环境，再执行：  
   `pip install -U crewai`
2. 网络稳定后从源码安装：  
   `pip install "git+https://github.com/crewAIInc/crewAI.git"`
3. 任务仅需「多 Agent 编排」时，可暂用 **LangGraph** 实现，待 CrewAI 环境就绪再迁移。

项目内已有 CrewAI 相关 **Agent Skills**（`.agents/skills/…`）时，仍以技能说明为准；**运行时代码**依赖 `crewai` 包时请先完成上述安装。

---

## 与后端工程的关系

- **不要**把上述库默认写进 `backend/requirements.txt`，以免扩大生产镜像、引入与 Flask 栈无关的冲突（例如不同版本的 `langchain-core`）。
- 若将来要把 RAG/Agent **并入** 后端服务，应单独开 issue：锁定版本、子进程/队列隔离、密钥与配额。

---

## 维护

新增或卸载任一类「Agent 常用 Python 库」时，请更新本文件，并在 [AGENTS.md](../AGENTS.md) 中若引用了本清单，核对链接仍有效。
