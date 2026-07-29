# API 接入说明（提交包）

本目录包含**已预配置的真实 API 凭证**（打包时从开发机注入），启动时会自动复制到 `source/backend/`：

| 文件 | 运行时目标 | 用途 |
|---|---|---|
| `backend.env.production-ready` | `source/backend/.env` | SQLite + `AGENT_BACKEND=auto` + DeepSeek/OpenAI 等 |
| `api-keys.spark.local` | `source/backend/.env.spark.local` | 讯飞 Spark Lite + 星辰 Agent（小E） |

## 接入能力

- **驿站小E / 自由问答**：讯飞星辰 Agent（`XFYUN_AGENT_*`）→ Spark → DeepSeek
- **个性化资源生成**：讯飞 Spark Lite（`IFLYTEK_SPARK_*`）
- **试炼编程辅导 / 教师 AI 出题**：DeepSeek（`DEEPSEEK_*`）
- **多智能体流水线**：`AGENT_BACKEND=auto`（CrewAI 可选 + LLM 增强）

## 源码位置（已在 `source/` 内）

- `source/backend/agents/` — 多智能体实现
- `source/backend/app/services/iflytek_spark.py` — 讯飞 Spark 客户端
- `source/backend/app/services/messenger_chat.py` — 驿站对话路由
- `source/backend/app/services/personalized_resource.py` — 资源生成流水线
- `source/backend/requirements-agents.txt` — CrewAI 依赖（启动时自动尝试安装）

## 验证 API 是否生效

启动后访问管理端 `/admin` → 系统观测，或调用：

```bat
cd source\backend
..\.venv\Scripts\python.exe scripts\smoke_iflytek.py
```

健康检查 `/api/v1/health` 中 `spark` / `xfyun_agent` 应显示 `configured: true`。

## 安全提示

`api-keys.spark.local` 与 `backend.env.production-ready` 含真实密钥，请勿上传到公开仓库；仅用于赛题提交包。
