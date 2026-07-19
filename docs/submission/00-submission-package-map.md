# PLEX A3 初赛提交材料地图

**整理日期**：2026-07-19  
**范围**：只整理配套文档，不修改源文件代码。  
**项目类型**：Web 应用；Vue 3 + Vite 前端，Flask + SQLAlchemy 后端，REST JSON API，JWT 认证。  

本文用于把初赛截图中的提交要求逐项落到仓库材料，避免提交时遗漏文件或混淆状态。

## 一、提交要求与材料映射

| 要求 | 应提交/引用的材料 | 说明 | 当前状态 |
|---|---|---|---|
| 演示 PPT | `docs/submission/12-defense-deck-spec.md`；目标产物 `docs/submission/artifacts/PLEX-A3-defense.pptx` | 10 页、7 分钟结构；每页必须绑定证据对象 | 规格已完成，正式 PPTX 待生成 |
| 多智能体相关文件 | `backend/agents/`、`backend/app/services/resource_audit/`、`backend/data/rag_docs/`、`backend/reports/`、配置样例和启动脚本 | 包含项目源码、课程知识库、报告、模型/后端配置说明；不得包含 `.env` 或真实密钥 | 文件组边界见 `14-freeze-file-groups.md` |
| 演示视频 | `docs/submission/10-demo-script.md`、`docs/submission/13-recording-runbook.md`；目标产物 `docs/submission/artifacts/PLEX-A3-demo.mp4` | 时长控制 7 分钟内，主备路线都要保留真实状态标识 | 脚本已完成，视频待录制 |
| 智能体开发类型 | `docs/submission/02-system-design.md`、`03-multi-agent-design.md` | Web 应用；多智能体流程作为学习资源生产、路径推荐和质量审核链路嵌入系统 | 已整理 |
| 配套文档 | `docs/submission/A3-PLEX-配套文档总册.md`、`docs/submission/01-14` 分册、`docs/submission/artifacts/PLEX-A3-supporting-documentation.docx` | 覆盖需求、设计、智能体、评测、测试、部署、手册、AI 工具说明、创新价值、演示材料 | 已补 Markdown 与 Word 总册 |
| AI Coding 工具说明 | `docs/submission/08-open-source-and-ai-tools.md`、总册第 10 节 | 说明 AI 辅助范围、人工复核责任、密钥与隐私边界 | 已整理 |

## 二、建议提交包目录

```text
PLEX-A3-submission/
├── source/                         # 候选源码与运行文件
├── data/                           # 课程知识库、演示数据说明或可公开数据集
├── config-samples/                 # .env.example 等配置样例，不放真实密钥
├── docs/                           # 本目录中的配套文档
├── reports/                        # backend/reports 与 frontend/reports 的最终报告
├── PLEX-A3-defense.pptx            # 正式演示 PPT
├── PLEX-A3-demo.mp4                # 7 分钟内演示视频
├── release-manifest.json           # 最终 SHA-256 清单
└── README.md                       # 提交包入口说明
```

实际打包时可以保留仓库原结构，但必须排除虚拟环境、依赖缓存、数据库、日志、上传目录、开发工具索引和真实凭证。排除规则以 `14-freeze-file-groups.md` 和最终 `release-manifest.json` 为准。

## 三、状态边界

| 类别 | 可写入口径 | 不可写入口径 |
|---|---|---|
| 本地规则后端 | 可说明 `local_rules` 支撑离线演示、确定性验收和指标报告 | 不可冒充真实讯飞 Spark 调用 |
| SQLite 本地验证 | 可说明本地开发、演示和确定性测试通过 | 不可冒充生产 MySQL 8 验收 |
| GitHub Actions | 可说明工作流已配置 | 无运行链接时不可写“在线 CI 已通过” |
| PPT 和视频 | 可说明脚本、规格和录制手册已完成 | 未生成文件前不可写“已提交 PPT/视频” |
| 当前工作树 | 可说明文档整理未改源代码 | 不可把脏工作树作为最终冻结版本 |

## 四、最终提交前检查

1. 运行 `start.bat --check`，确认后端、前端、数据库迁移、演示账号和健康检查通过。
2. 后端执行全量测试、知识库校验、安全校验、性能恢复校验和密钥扫描。
3. 前端执行 `npm run build`，并确认 bundle budget 报告通过。
4. 配置真实讯飞凭证后执行画像、资源、驿站三项真实冒烟，报告中记录模型、请求 ID、延迟和实际后端。
5. 在 GitHub Actions 归档 Python 3.12、Node 20、MySQL 8 工作流链接与 artifacts。
6. 在干净工作树重新生成 `release-manifest.json` 和 `release-readiness.json`。
7. 生成正式 `PLEX-A3-defense.pptx`，按 `13-recording-runbook.md` 录制 `PLEX-A3-demo.mp4`。
8. 核对 PPT、视频、总册、README、报告指标和提交 SHA 是否一致。

## 五、人工确认项

- 根目录四个 `PLEX *.pdf` 是否作为赛题原型依据进入提交包；若仅为历史参考，应从最终包中排除或单独归档。
- `picture/` 下素材是否被正式前端、PPT 或文档引用；未引用素材不进入候选包。
- 当前未提交源代码修改是否属于同一功能阶段；最终冻结前应拆分、审查并形成明确提交 SHA。
