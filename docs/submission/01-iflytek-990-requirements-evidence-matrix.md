# PLEX × 科大讯飞新工科 990 命题

## 需求—实现—测试—证据矩阵

> 口径：`已验证` 仅表示当前代码、自动化测试或报告已经证明；`待外部` 表示必须取得讯飞权限、真实学生或企业/学校材料后才能验收；`待补` 表示仍需本地工程工作。Mock、本地规则、真实 API 分开记录，不互相替代。

| 命题要求 | 当前实现 | 验证方式 | 证据 | 状态 / 缺口 |
|---|---|---|---|---|
| ≥6 维动态学习者画像 | 学习基础、目标、偏好、节奏、错因、行为等画像字段；行为更新与历史证据链 | 后端画像/学习路径测试；50 条本地画像评测 | `backend/reports/iflytek-990-profile-extraction-20260828.json` | 已验证本地规则；真实学生画像待外部 |
| ≥100 知识节点、≥200 关系 | 8 类课程知识图谱，100 节点、256 条唯一关系 | 图谱完整性、环检测、关系类型校验 | `backend/reports/iflytek-990-kg-validation-20260828.json` | 已验证 |
| 多智能体协同 | 画像、检索、教学设计、资源生成、审核、路径等 Agent；任务依赖、重试字段持久化 | 编排脚本 + 稳定性测试 | `backend/reports/iflytek-990-agent-orchestration-20260828.json` | 已验证本地/mock；真实星火模型待外部 |
| ≥100 条自然语言意图路由，准确率 ≥90% | 缺省 intent 关键词兜底与显式路由 | 100 条契约样本 + 100 条自然语言样本 | `backend/reports/iflytek-990-intent-dispatch-20260828.json` | 已验证本地规则 100%；真实学生语料待外部 |
| ≥5 类个性化学习资源 | 学习包、讲义、导图、分层题库、代码实操、拓展阅读 | 资源生成与 schema/引用检查 | `backend/tests/test_personalized_resources.py` | 已验证 6 类；视频/数字人资源仍待接入 |
| RAG + 知识图谱约束 | 100 份课程 RAG 文档、引用绑定知识点和课程文档 ID | 100 节点本地清洁样本与 10 个伪造引用负对照 | `backend/reports/iflytek-990-hallucination-local-20260828.json` | 本地硬风险率 0%、负对照检出 100%；真实讯飞幻觉率待外部 |
| 幻觉率 ≤5% | 引用、越界、代码、重复、结构风险检测；教师审核阻断 | 本地规则基准脚本 | 同上 | 不能宣称真实模型达标，待 100 条讯飞输出 |
| SM-2 错题复习闭环 | 到期队列、复习提交、画像/掌握度/路径重规划、每日任务和教师快照；前端反馈展示路径前后 active node | 后端错题/学习路径测试；端到端失败—复习—重规划脚本；前端生产构建 | `docs/2026-08-28-iflytek-990-kg-sm2-progress.md`；`backend/reports/iflytek-990-path-replanning-20260828.json` | 本地闭环与路径变化展示已验证；真实学生轨迹待外部 |
| 风险预警与教师干预 | 风险因子、证据、确定性贡献、工单状态流转、教师摘要；看板展示干预完成率 | evaluation/teacher API 测试；解释契约探针；教师看板验收清单 | `docs/2026-08-28-iflytek-990-completion-audit.md`；`backend/reports/iflytek-990-risk-explainability-20260828.json`；`docs/2026-08-28-iflytek-990-teacher-dashboard-acceptance.md` | 本地解释与干预统计已验证；真实训练数据与浏览器录屏待补 |
| 语音交互首 Token ≤1.5s | 流式消息已回传 context/first-token/generation 指标；ASR/TTS 探针 | 语音管线探针 | `backend/reports/iflytek-990-voice-20260828.json` | 指标已埋点；ASR/TTS/数字人和 P95 尚未实测 |
| ≥30 轮连续语音稳定性 | 已完成 30 轮本地 TTS 合成测量；ASR/播放阶段仍无适配器 | 需在真实权限和设备上运行完整语音回合 | `backend/reports/iflytek-990-voice-20260828.json` | 部分验证（TTS 30 轮）；完整语音待外部 |
| ≥100 人次真实教学实验 | 脱敏事件模板、分析脚本、方案和数据字典；脚本含 PII/重复事件/缺失字段校验 | 真实课程前/后测、时长、完成率、接受率、满意度；统计输出含均值、标准差、中位数 | `docs/2026-08-28-iflytek-990-真实教学实验方案.md`；`backend/reports/iflytek-990-experiment-20260828.json` | 工程准备已验证；待外部，当前 0 人次 |
| 参赛材料 | 10 页路演底稿、系统说明、证据报告和 PPTX 已形成 | 2 轮本地 API 全流程彩排通过；PPTX 视觉质检已通过；仍需录制 MP4、真实环境彩排 | `docs/submission/15-iflytek-990-defense-script.md`；`docs/submission/artifacts/PLEX-iflytek-990-defense.pptx`；`backend/reports/iflytek-990-demo-rehearsal-20260828.json` | Markdown/PPTX/本地彩排已验证；MP4 与真实环境待补 |

## 统一验收原则

逐项完成审计报告：`backend/reports/iflytek-990-completion-audit-20260828.json`。该报告将每条要求标记为 `verified_local`、`blocked_external` 或 `missing`，并以 `submission_ready` 作为总闸门；当前仍有 5 项外部闸门未关闭。

1. 任何“真实讯飞”结论必须有请求 ID、模型、时间、输入摘要、输出摘要、耗时和错误记录。
2. 任何“真实教学效果”结论必须有授权/脱敏记录、样本数、对照方案、统计方法和原始事件哈希。
3. 本地规则和 Mock 结果只能证明工程链路和防线有效，不能替代企业接口或真实学生效果。
4. 目标日期为 **2026-10-01**；在外部材料到位前，清单中的待外部项保持未完成。
