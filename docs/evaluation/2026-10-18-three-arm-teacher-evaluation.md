# 教师冻结集的三方案评测与回答评分

状态：运行器和评分校验工具已实现；实际教师基线仍为 120 条待审候选、0 条实审。本轮没有进行付费模型实验，没有正式教学质量成绩。测试中的模型、评审声明和分数均为 pytest 临时夹具。

本流程衔接[教师基线填写与冻结](2026-10-18-teacher-baseline-workflow.md)，不修改 `evaluate_knowledge_retrieval.py` 的合成工程回归口径。

## 比较的具体内容

| 方案 | 实际执行路径 | 边界 |
| --- | --- | --- |
| direct_model | 同一固定模型直接接收问题、代码和学生附带的题目说明 | 没有课程检索；提示要求不编造来源或执行结果，不默认代做完整答案 |
| course_rag | 当前 `KnowledgeRagService.prepare/generate` | 保留图谱、混合检索、去冗余与教学策略，使用无学习历史的上下文；没有显式小 E 模式契约和二次模型审核 |
| full_tutor | 当前 `MessengerTutoring.prepare/answer`，经 `TutorService` 的上下文检查、意图路由、检索、生成和审核 | 沿用真实聊天入口的低证据处理，包括规则回退；不在评测中另设一套更严格拒答策略 |

course_rag 是当前课程 RAG 的受控比较配置，**不是历史代码回放，也不是移除了图谱的普通向量 RAG**。当前冻结集没有真实学习历史，三种方案均处于新用户场景。full_tutor 的状态版本为 0，掌握度和误概念保持未知；本轮比较不能证明学习状态个性化的增益。状态消融已增加独立的[状态可见／屏蔽协议](2026-10-18-state-availability-evaluation.md)，需要另行审核冻结历史并保持其他变量不变；原三方案仍保持冷启动口径，尚无真实状态消融结果。

这些是同模型的系统方案比较，提示、检索与审核环节不同；不能把方案差异单独归因于某一个组件。

## 隔离与可复现信息

- 只接受通过 `verify_frozen` 的人工声明审核文件。未冻结、摘要变化、跨组、覆盖不足的材料不能运行；重复正文的课程文档须整理成新数据版本后重新审核，不能当成多份独立材料。
- 每次新建临时 SQLite 数据库和内存向量索引，只导入此次批准的课程文本、课程图谱结构及虚拟学生。结束后关闭并移除临时数据库，不读取主库学生、聊天或学习记录，不执行候选代码，也不创建真实注册账号。
- 使用本地哈希 Embedding，配置在运行清单中明确记录。这不是训练型语义嵌入质量实验；不能把此处结果直接冒充另一套线上 Embedding/向量库配置的结果。
- 教师意图标签、相关性分、答案要点、拟知识点和边界标签只用于选集和评测，不进入检索查询或模型输入。学生附带题目只有 title/prompt，不伪装为服务器正式试题；没有伪造运行记录。
- 固定同一供应商端点和配置模型；实际响应必须带 model，并在整个运行中保持一致。模型别名不代替实际模型证明；实际模型变化或缺失时中止并标记不完整。
- 三方案生成温度均为 0.1、输出上限 1300 token、超时 22 秒，保留模型原始文本。小 E 的额外审核仍有单独调用，温度 0.1、上限 220 token、超时 12 秒；因此模型调用数、总延迟和费用不能假设相同。
- 顺序执行，随机化方案/案例顺序并保存 seed；禁止透明 HTTP 重试。记录每次实际 POST 的 request_id、方案、阶段、实际模型、token、耗时、错误类型、提示摘要与配置，不写 API 密钥、请求头或供应商响应错误正文。
- 保存冻结输入、实现摘要、检索/策略配置、各题回答、候选来源及版本、调用清单和输出完整性索引。已有输出目录拒绝覆盖；中断后选择新目录重新运行，不静默重试或从多次结果中自动挑选最好的一次。代码运行期间变化也标记为不完整。

## 运行顺序

先由真实教师完成输入审核并冻结；**当前尚未满足这一步**。以下命令都在仓库根目录运行。第一次只准备清单，不发模型请求：

```powershell
.venv/Scripts/python.exe backend/scripts/evaluate_teacher_baseline.py --frozen output/plex-teacher-baseline-v1/frozen-review-v1.json --output output/teacher-eval-plan-v1 --split development
```

检查清单后，用新目录执行一个有明确调用上限的小批次：

```powershell
.venv/Scripts/python.exe backend/scripts/evaluate_teacher_baseline.py --frozen output/plex-teacher-baseline-v1/frozen-review-v1.json --output output/teacher-eval-development-pilot-v1 --split development --max-cases 3 --max-calls 12 --execute-model-calls
```

`--execute-model-calls` 才会产生实际模型调用，可能计费。`--max-calls` 限制 HTTP 调用次数，不是货币预算；默认 500 次。模型响应 token 缺失会记为空，不当成免费。`--max-cases` 是按固定案例 ID 顺序截取，清单会标出 `complete_split=false`，不能称为完成整组评测。

正式实验取消 `--max-cases`，固定配置分别运行 development 和 test。测试结果不得反复用来调参；原始失败、拒答、规则回退和缺失对照都要保留。`report.json` 的 completed 只表示执行完整，**不是回答质量审核完成**。

## 输出与教师交接

仅将以下文件的副本交给评分者：

- `blind-review.json`：回答评分模板，所有分数和评审者初始为空。保留原件，另存为 `teacher-scores-v1.json` 后填写。
- `approved-course-materials.json`：完整批准材料。来源预览最多 2200 字，截断时有 `preview_truncated=true`，教师可按材料 ID、版本和摘要对照完整正文。
- 本说明中的评分规则。

不要将 `manifest.json`、`result-*.json`、`report.json`、`private-arm-map.json` 一起交给盲评者，它们包含方案对应关系或运行信息。模板隐藏方案和模型名称、打乱顺序，但回答风格与来源数量可能泄露方案，因此不能宣称实现了严格双盲。

临时课程来源不能用正式站点的 URL 打开。评分包引用改为离线材料 ID/版本/摘要，不附上已失效的临时 API 地址。课程材料、填过的教师记录和模型回答默认保存在 Git 忽略的 output 下，不自动上传。

## 教师评分规则

在 reviewers 中填写代号以及 `declares_python_teaching_experience=true`、`declares_personal_review=true`。每条回答填 reviewer_id、实际且带时区的 reviewed_at、rationale 和以下字段。工具只能检查声明与结构，不能认证真人或代替审核负责人。

| 字段 | 评分口径 |
| --- | --- |
| correctness | 0：关键结论错误；1：明显遗漏/误导；2：基本正确但有小问题；3：正确且边界清楚 |
| evidence_support | 0–3：从关键结论无支持到来源充分支持；无须课程引用的情况可明确填写字符串 not_applicable |
| teaching_action | 0–3：从不符合当下需求到能恰当解释、定位、核对或澄清 |
| actionable_next_step | 0–3：从无可操作动作到学生能够独立执行；本题无需下一步可填写 not_applicable |
| answer_leakage | true/false：在请求提示或检查思路的约束下是否泄露完整解法；短代码、伪代码和自然语言也需要检查 |
| over_refusal | true/false：在上下文与材料足够时是否不必要地拒答；必要澄清不算过度拒答 |

未评分保持 null，不填 0 代替“未审”。不得修改题面、回答、来源或 review_id。必要时记录分歧，人工解决后形成最终一份标注；当前工具不实现多评审投票或一致性系数。

```powershell
.venv/Scripts/python.exe backend/scripts/check_teacher_answers.py --run output/teacher-eval-development-pilot-v1 --reviews output/teacher-scores-v1.json --report output/teacher-answer-report-v1.json
```

退出码 2 表示待人工评分或实验不完整；退出码 1 表示结构、内容摘要、时间或评分非法。工具不信任手填的 reviewed 数量和 status，按每条记录重新计算。只有三方案成对执行完整、每条回答都有合格声明及全部评分时，才输出质量汇总。输出报告必须是新文件且位于不可变运行目录外。

## 指标解释与未完成事项

检索输出文档级 Recall@6、nDCG@6：按文档去重，匹配教师材料 ID、版本和正文摘要，相关性使用教师的 1/2/3 分。没有课程相关性标注的案例显示 null，不按 0 拉低平均；未标注材料视为无相关性，因此标注覆盖不足会影响指标。缺上下文场景是否该澄清，要看教师的教学动作评分，不能用检索命中代替。

回答的 0–3 平均分是序数评分摘要；泄题/过度拒答同时给出分子与分母。not_applicable 单列，不当成 0。未评分时 quality_metrics 始终为空，不计算模型自评分来冒充教师评分。不完整实验、子集或真实模型未统一的结果不能充当完整三方案质量对照。

本轮没有完成真实教师标注、付费模型对照、状态个性化消融、隔离执行轨迹核验、长期学习收益或课堂试用。工程测试通过不能替代这些门槛。
