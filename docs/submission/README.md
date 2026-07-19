# PLEX A3 正式交付文档入口

本目录用于整理初赛提交所需的配套材料。所有功能、指标和演示表述必须能够回溯到仓库代码、`backend/reports/`、自动化测试、运行中的接口，或明确标记的外部验收记录。

## 提交要求对照

| 截图要求 | 对应材料 | 当前状态 |
|---|---|---|
| 演示 PPT | `12-defense-deck-spec.md`；最终文件目标为 `artifacts/PLEX-A3-defense.pptx` | 规格已整理；正式 PPTX 尚未生成 |
| 可完整运行的多智能体相关文件 | `14-freeze-file-groups.md`；`backend/reports/a3-submission/release-manifest.json` | 候选清单已有历史报告；最终冻结前需重跑 |
| 7 分钟内演示视频 | `10-demo-script.md`、`13-recording-runbook.md`；最终文件目标为 `artifacts/PLEX-A3-demo.mp4` | 脚本与录制手册已整理；视频待录制 |
| 智能体开发类型 | `00-submission-package-map.md`、`02-system-design.md`、`03-multi-agent-design.md` | Web 应用，Vue 3 + Flask 前后端分离 |
| 配套文档 | `A3-PLEX-配套文档总册.md`、`01-14` 分册、`artifacts/PLEX-A3-supporting-documentation.docx` | 已补总册入口与 Word 版 |
| AI Coding 工具说明 | `08-open-source-and-ai-tools.md`、总册第 10 节 | 已整理责任边界 |

## 文档结构

| 文件 | 用途 |
|---|---|
| `00-submission-package-map.md` | 按初赛提交要求映射材料、目录和缺口 |
| `01-requirements.md` | 项目需求分析说明 |
| `02-system-design.md` | 系统设计与开发说明 |
| `03-multi-agent-design.md` | 多智能体设计说明 |
| `04-knowledge-and-evaluation.md` | 课程知识库与评测数据说明 |
| `05-testing.md` | 系统测试说明 |
| `06-deployment.md` | 部署与运行说明 |
| `07-user-manual.md` | 用户操作手册 |
| `08-open-source-and-ai-tools.md` | 开源软件、许可证与 AI 工具说明 |
| `09-innovation-and-value.md` | 创新点与应用价值说明 |
| `10-demo-script.md` | 七分钟演示脚本 |
| `11-external-acceptance-checklist.md` | 外部验收清单 |
| `12-defense-deck-spec.md` | 答辩 PPT 规格 |
| `13-recording-runbook.md` | 七分钟演示录制执行手册 |
| `14-freeze-file-groups.md` | 最终冻结文件分组 |
| `A3-PLEX-配套文档总册.md` | 可转 Word 的提交说明总册 |
| `artifacts/PLEX-A3-supporting-documentation.docx` | Word 版配套文档总册 |

## 状态口径

- **已真实验收**：真实运行环境或真实外部服务已执行并留存证据。
- **本地验收**：SQLite、本地规则后端或确定性测试通过，不等同真实大模型或生产 MySQL。
- **外部阻塞**：代码或脚本已准备，但缺少凭证、联网 CI、MySQL 8 环境或可归档运行链接。
- **待交付**：PPTX、MP4、最终提交包等材料尚未生成或尚未人工确认。
- **未实现**：不得在答辩、PPT 或视频中表述为已完成功能。

## 当前整理结论

截至 2026-07-19，本次整理未修改源文件代码。`backend/reports/a3-submission/release-readiness.json` 的历史报告显示本地证据齐全，但 `submission_ready` 仍为 `false`，主要阻塞为真实讯飞验收、GitHub 在线 CI、MySQL 8、干净工作树、正式 PPTX 和演示视频。

最终提交前应在干净工作树重新运行候选清单和发布就绪检查，确保文档、PPT、视频、代码版本和证据文件完全一致。
