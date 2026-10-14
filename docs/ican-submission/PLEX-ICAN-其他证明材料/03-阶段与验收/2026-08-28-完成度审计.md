# 科大讯飞新工科 990 完成度审计（2026-08-28）

本表按企业命题口径检查当前工作树。`已验证` 只表示有当前代码、脚本和可复现实测证据；`部分完成` 不得在答辩中表述为达标。

| 指标 | 当前状态 | 证据 | 仍需关闭 |
|---|---|---|---|
| 动态学习者画像 | 部分完成 | `student_profile` 数据、历史留痕、50 条本地规则抽取评测（准确率/召回率/特异度 1.0） | 真实模型抽取与真实学生语料复核 |
| 知识图谱 ≥100 节点 | 已验证 | 100 节点统计、注册表 | 节点实体层级需进一步补充 |
| 知识图谱 ≥200 关系 | 已验证 | 256 条唯一边 | 无 |
| 关系语义覆盖 | 已验证 | 图谱校验报告覆盖 10 类关系 | 教师人工审核语义 |
| 图谱完整性 | 已验证 | 无孤立、重复、非法引用；前置无环 | 无 |
| 到期复习驱动路径 | 已验证 | SM-2 队列、路径 due bonus、回归测试 | 浏览器录屏 |
| 多智能体 ≥6 | 已验证 | 9 学习 Agent、8 评分 Agent | 真实模型后端 |
| 编排 trace/依赖/重试 | 已验证 | Agent trace、任务 steps、retry_count | 消息队列或跨进程持久化压测 |
| 意图路由 ≥90% | 部分完成 | 100 条人工构造自然语言样本 100% | 真实学生语料复核 |
| 多模态资源 ≥5 类 | 部分完成 | 本地规则资源生成和资源类型注册 | 真实模型 100 条事实核验 |
| 幻觉率 ≤5% | 未验证 | 本地风险规则可运行 | 真实讯飞输出与统一核验集 |
| ASR/TTS/数字人 | 部分完成 | TTS 适配器、流式首 Token 埋点 | ASR、情感 TTS、唇音同步、30 轮实测 |
| 首 Token P95 ≤1.5s | 未验证 | 运行时 latency 字段 | 真实环境 P95 报告 |
| SM-2 四联动 | 已验证 | 错题→复习→画像→图谱→路径测试 | 真实课程数据 |
| 风险解释 | 部分完成 | 确定性贡献因子和证据 | 真实/脱敏训练集、SHAP 或同等级模型 |
| 教师工单 | 部分完成 | LearningAdaptation ticket 查询/更新 API | 指派、复核、关闭的前端全流程 |
| 教师风险看板 | 部分完成 | 班级评估、主要风险因子摘要 | 浏览器验收录像、干预完成率图表 |
| 真实课程实验 | 未验证 | 协议、脱敏模板、统计脚本 | ≥100 人次、教师证明、效果报告 |
| 路演材料 | 部分完成 | 10 分钟 Markdown 路演稿 | 正式 PPTX、MP4、最终提交包 |

## 当前不可冒充的外部条件

1. 讯飞 Spark/ASR/TTS 凭证、请求编号和真实延迟日志。
2. 合作教师、课程、学生知情与脱敏记录。
3. 至少 100 人次前测—干预—后测事件。
4. 正式浏览器录屏、PPTX 和 MP4。

## 运行入口

```text
py -3 backend/scripts/validate_knowledge_graph.py
py -3 backend/scripts/evaluate_intent_dispatch.py
py -3 backend/scripts/evaluate_iflytek_live.py --cases 100
py -3 backend/scripts/evaluate_voice_pipeline.py
py -3 backend/scripts/analyze_iflytek990_experiment.py --input backend/data/experiments/iflytek990_event_template.csv --output backend/reports/iflytek-990-experiment-20260828.json
```
