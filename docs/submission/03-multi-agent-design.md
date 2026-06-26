# 多智能体设计说明

资源生产线包含六个显式角色：

1. `profile_interpreter`：将七维画像转换为教学约束。
2. `knowledge_retriever`：检索白名单知识点、章节和引用。
3. `instructional_designer`：确定难度、顺序、案例和练习层次。
4. `resource_generator`：生成五类结构化学习资源。
5. `quality_reviewer`：执行 Schema、引用、安全、重复和代码检查。
6. `path_planner`：形成星轨位置、推荐理由和下一步学习建议。

每一步消费上一步结构化产物，并在任务中保存角色、契约版本、依赖、输入输出脱敏
摘要、耗时、后端、模型、状态和失败原因。前端展示审计摘要，不展示系统提示词或
完整个人数据。

无讯飞凭证时使用 `local_rules` 后端，页面明确显示实际后端。真实 Spark 调用仍是
外部阻塞，只有 `smoke_iflytek.py` 留存模型、请求 ID、延迟和后端证据后才能升级
为真实验收状态。CrewAI 为可选运行时，不进入默认生产依赖。
