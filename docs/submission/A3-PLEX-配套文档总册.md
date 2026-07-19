# A3 / PLEX 个性化学习系统配套文档总册

**整理日期**：2026-07-19  
**文档用途**：初赛配套文档、评审说明、PPT 和演示视频口径来源  
**Word 版**：`docs/submission/artifacts/PLEX-A3-supporting-documentation.docx`  
**项目类型**：Web 应用，多智能体能力嵌入个性化学习闭环  
**整理边界**：本次只整理文档，不修改源文件代码  

## 1. 项目概述

A3 / PLEX 是面向 Python 程序设计初学者的个性化学习系统。系统以学生、教师、管理员三类角色为核心，围绕“画像 - 资源 - 作答 - 反馈 - 路径 - 审核”的学习闭环组织功能。

学生端通过画像、资源中心、星轨路径、今日委托、试炼和成长档案获得个性化学习反馈；教师端通过班级总览、学生档案、资源审核和知识风险观测完成教学干预；管理员端观察健康状态、任务后端、降级比例、安全风险和系统配置。

项目采用前后端分离架构：

| 层级 | 技术选型 | 说明 |
|---|---|---|
| 前端 | Vue 3 + Vite + Naive UI + Pinia + Axios | 正式前端唯一目标栈 |
| 后端 | Flask + SQLAlchemy + Flask-JWT-Extended | REST JSON，统一 `/api/v1` 前缀 |
| 数据库 | MySQL 8（生产目标）/ SQLite（本地演示） | SQLAlchemy 抽象保证迁移与本地演示便利 |
| 认证 | JWT Access + Refresh | 适合前后端分离和多端权限控制 |
| AI / 智能体 | 讯飞 Spark / local_rules / CrewAI 可选运行时 | 真实大模型验收与本地规则验收严格区分 |

当前仓库本地默认入口为前端 `http://localhost:5180`，后端 `http://127.0.0.1:5100`，以根目录 `start.bat`、`frontend/.env.development` 和 `backend/QUICKSTART.md` 为准。

## 2. 初赛提交要求对照

| 初赛要求 | 本项目对应材料 | 当前处理 |
|---|---|---|
| 演示 PPT | `docs/submission/12-defense-deck-spec.md` | 已有 10 页结构规格；正式 PPTX 待生成 |
| 可完整运行的多智能体相关文件 | `backend/agents/`、`backend/app/services/resource_audit/`、`backend/data/rag_docs/`、`backend/reports/`、配置样例和启动脚本 | 最终纳入范围见 `14-freeze-file-groups.md` |
| 7 分钟内演示视频 | `10-demo-script.md`、`13-recording-runbook.md` | 演示脚本和录制手册已整理；MP4 待录制 |
| 智能体开发类型 | Web 应用，Vue + Flask 前后端分离 | 已在系统设计与本总册中说明 |
| 配套文档 | 本总册、`01-14` 分册和最终 DOCX | 已补充统一入口 |
| AI Coding 工具说明 | `08-open-source-and-ai-tools.md` 和本总册第 10 节 | 已写明辅助范围、人工复核与密钥边界 |

## 3. 核心需求

系统面向统一教学内容难以适配不同基础、目标、表达偏好和学习节奏的问题，核心需求包括：

- 学生通过自然语言与行为数据形成动态画像，画像至少覆盖基础、目标、偏好、易错点、节奏、兴趣等维度。
- 多智能体读取画像和课程知识库，生成讲解文档、思维导图、分层练习、拓展阅读和代码实操五类资源。
- 系统根据作答、错题和画像变化调整学习路径与推荐。
- 教师审核低置信度资源，查看班级薄弱点、学习效果和干预依据。
- 管理员观察实际后端、健康状态、任务成功率、风险和降级状态。
- 系统提供 JWT 权限隔离、课程范围限制、提示注入防护、引用校验、上传安全、任务幂等和失败恢复。

## 4. 系统设计

系统设计强调同一事实源。学生成长档案和教师学生档案调用同一学习效果服务；推荐与星轨共享画像和薄弱点排序；待审核资源在批准前不向学生发布；管理员端展示实际模型后端和降级原因。

| 模块 | 面向用户 | 关键能力 |
|---|---|---|
| 学生画像 | 学生、教师 | 画像抽取、字段来源、置信度、版本记录、建议确认 |
| 个性化资源 | 学生、教师 | 五类资源生成、引用、置信度、审核状态、实际后端标识 |
| 星轨路径 | 学生 | 六大学域知识点导航、路径推荐、内嵌练习入口 |
| 试炼与错题 | 学生、教师 | 教师发布、学生作答、错题记录、反馈闭环 |
| 教师审核 | 教师 | 风险原因、审核说明、批准/驳回、学生可见性控制 |
| 管理观测 | 管理员 | 健康、任务后端、降级、性能、安全、冻结闸门 |

## 5. 多智能体方案

资源生产线包含六个显式角色：

| 角色 | 职责 |
|---|---|
| `profile_interpreter` | 将学生画像转换为教学约束 |
| `knowledge_retriever` | 检索白名单知识点、章节和引用 |
| `instructional_designer` | 确定难度、顺序、案例和练习层次 |
| `resource_generator` | 生成讲解、导图、练习、阅读和代码实操 |
| `quality_reviewer` | 执行 Schema、引用、安全、重复和代码检查 |
| `path_planner` | 形成星轨位置、推荐理由和下一步建议 |

每一步保存角色、契约版本、依赖、脱敏输入输出摘要、耗时、实际后端、模型、状态和失败原因。前端展示审计摘要，不展示系统提示词或完整个人数据。

无真实凭证时系统使用 `local_rules` 后端，并在界面和报告中明确显示实际后端。只有真实请求报告留存模型名、请求 ID、延迟和后端证据后，才能把讯飞 Spark 标记为真实验收。

## 6. 知识库与评测

课程范围固定为 Python 程序设计基础，历史报告覆盖 16 个知识点。每个知识点拥有唯一 `document_id`、章节、概念、正反例、常见错误、基础练习、进阶练习和来源。

评测证据来自 `backend/reports/`：

| 证据 | 历史报告状态 |
|---|---|
| `a3-personalization-local/personalization-evaluation.json` | 双画像、16 个知识点、五类资源，本地规则验收通过 |
| `a3-personalization-local/profile-extraction-evaluation.json` | 画像抽取评测通过 |
| `a3-personalization-local/knowledge-base-validation.json` | 知识库结构校验通过 |
| `a3-personalization-local/feedback-loop-three-rounds.json` | 三轮反馈闭环通过 |
| `a3-next-stage/learning-effect.json` | 前后三次作答证据充分，正确率变化 +100 个百分点 |
| `a3-next-stage/security-validation.json` | 8/8 安全专项通过 |
| `a3-next-stage/performance-recovery.json` | 并发成功率 100%，幂等率 100%，P95 173.79 ms |

这些结果属于 2026-06-12 历史本地证据，使用 SQLite 和 `local_rules`，不代表真实讯飞或生产 MySQL 性能。

## 7. 运行与部署

推荐环境为 Windows 10/11 或 Linux、Python 3.12、Node.js 20、npm 和 MySQL 8。本地演示可使用 SQLite。

Windows 根目录入口：

```bat
start.bat --check
start.bat
```

当前默认地址：

| 服务 | 地址 | 来源 |
|---|---|---|
| 前端 | `http://localhost:5180` | `frontend/.env.development`、`start.bat` |
| 后端 | `http://127.0.0.1:5100` | `frontend/.env.development`、`backend/QUICKSTART.md` |
| API 前缀 | `/api/v1` | `backend_api_design.md` |

生产环境必须通过环境变量配置数据库、JWT 密钥和模型凭证。不得提交 `.env`、真实讯飞密码、访问令牌、个人数据数据库或上传目录。

## 8. 测试与证据

历史发布就绪报告 `backend/reports/a3-submission/release-readiness.json` 显示：

| 项目 | 状态 |
|---|---|
| 本地证据 | `local_passed: true` |
| 正式提交 | `submission_ready: false` |
| 个人化、画像、知识库、反馈闭环、学习效果、安全、性能、干净环境、依赖、弃用预算、发布清单、答辩指标、前端 bundle | 报告存在且通过 |
| 讯飞 Spark、GitHub 在线 CI、MySQL 8 | 外部阻塞 |
| 正式 PPTX、演示视频 | 待交付 |
| 工作树 | 历史报告生成时不是干净状态 |

最终提交前必须在干净工作树重新生成 `release-manifest.json` 和 `release-readiness.json`，并确认 PPT、视频、文档和提交 SHA 完全一致。

## 9. PPT 与演示视频

正式答辩 PPT 建议采用 `12-defense-deck-spec.md` 的 10 页结构：

1. 封面：PLEX 是面向 Python 课程的可审计个性化学习闭环。
2. 问题与方案：统一内容无法适配不同学生。
3. 闭环架构：系统不是独立聊天框，而是贯穿三角色和数据库事实的教学系统。
4. 七维动态画像：画像具备来源、置信度、确认和版本历史。
5. 六角色资源工厂：五类资源由可追踪职责链生成并接受审核。
6. 个性化差异证据：同一知识点因画像变化产生可量化差异。
7. 学习反馈与效果：系统拒绝在样本不足时输出提升结论。
8. 安全与人机协同：生成内容经过输入、检索、生成、发布四层控制。
9. 工程可信度：可重复启动、零项目弃用、性能预算和候选包审计。
10. 真实状态与演示收束：已验收、外部阻塞和未实现项严格分开。

七分钟视频按 `10-demo-script.md` 与 `13-recording-runbook.md` 执行。视频必须录入实际后端字段，不隐藏 `local_rules` 或降级原因，不用 Mock 截图替代真实操作。

## 10. 开源与 AI Coding 工具说明

项目依赖清单由 `backend/reports/a3-submission/dependency-inventory.json` 生成，历史报告显示运行依赖版本和许可证均可解析。前端直接依赖包括 Vue、Vite、Naive UI、Pinia、Axios、AntV G6、ECharts、Vue Flow、Monaco、Uppy、Driver.js 和 Fuse.js；后端依赖包括 Flask、SQLAlchemy、JWT、Alembic、Marshmallow、PyMySQL、Requests 和 JSON Schema。

开发过程中使用 AI Coding 工具辅助需求拆解、代码实现、测试设计和文档整理。所有生成内容均由团队通过代码审查、自动化测试、运行验证和人工演示复核；最终代码、数据、引用和答辩表述责任由参赛团队承担。不得向 AI 服务发送真实密钥、访问令牌、学生隐私或未脱敏个人数据。

CrewAI 是独立可选智能体运行时，不应在默认生产依赖和正式演示口径中冒充已真实接入的大模型链路。

## 11. 当前风险与阻塞

| 阻塞 | 影响 | 关闭条件 |
|---|---|---|
| 讯飞 Spark 真实凭证未完成验收 | 不能宣称真实大模型已通过 | 留存画像、资源、驿站三项真实请求报告 |
| GitHub 在线 CI 未归档 | 不能宣称在线 CI 已通过 | 归档工作流 URL、提交 SHA、Job 结论和 artifacts |
| MySQL 8 未实测 | 不能宣称生产数据库验收通过 | 全新 MySQL 8 数据库迁移、种子和核心闭环报告 |
| 正式 PPTX 未生成 | 不能提交完整 PPT 材料 | 生成并人工检查 10 页 PPT |
| 7 分钟 MP4 未录制 | 不能提交完整视频材料 | 按主备路线录制、压缩并核对口径 |
| 工作树有源代码修改 | 不能冻结最终包 | 审查、提交或明确排除后重新生成清单 |

## 12. 最终提交清单

- 源码与运行文件：按 `14-freeze-file-groups.md` 纳入，不包含虚拟环境、依赖缓存、数据库、日志、上传目录和真实凭证。
- 数据与知识库：纳入公开课程知识库、演示数据说明和可重复报告。
- 配置：只提交 `.env.example` 等样例，不提交真实密钥。
- 文档：提交本总册、`01-14` 分册、README、`artifacts/PLEX-A3-supporting-documentation.docx` 和必要的运行说明。
- PPT：提交 `PLEX-A3-defense.pptx`。
- 视频：提交 `PLEX-A3-demo.mp4`，时长控制在 7 分钟内。
- 报告：提交最终 `release-manifest.json`、`release-readiness.json`、依赖清单、测试报告、安全报告、性能报告和前端 bundle 报告。
- 版本：记录最终 Git 提交 SHA，确认清单与提交包逐项一致。
