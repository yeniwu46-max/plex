# 学习状态可见／屏蔽的成对评测

这是原三方案冷启动比较之外的第二种协议，`teacher-state-availability-v1`。工程工具已接入；当前课程基线仍未完成真实教师标注，没有被冻结的历史包，也没有实际模型对照、人工回答评分或个性化增益结果。

## 比较什么

| 条件 | 运行方式 |
| --- | --- |
| `tutor_state_masked` | 在隔离评测库重放批准的同一段历史，但向 TutorService 提供未知状态快照 |
| `tutor_state_visible` | 重放同一段历史，向 TutorService 提供当前 LearnerStateService 计算的完整快照 |

两边均使用 `MessengerTutoring.prepare/answer`、相同模型/参数、课程资料、Embedding、检索配置、审核流程、新会话和空偏好画像。状态影响检索、先修建议和教学动作，是本实验有意改变的输入；不是将完整系统与直接问模型混为一次单组件消融。

每题每条件单独创建虚拟学生；两边数据库中都存在相同的声明历史，只有提供给辅导的快照被屏蔽或开放。历史不来自主库导出，代码不执行。回放只能在运行器新建的 `evaluation.sqlite` 中开启，不接受生产数据库。服务端协议中的“正式判题”类型在此用于重放声明的过去观察，结果显式标记 `state_projection_is_new_measurement=false`，**不能当成新发生的真实判题或真实学习证据**。

固定 `as_of` 作为历史是否过期、复习是否到期及教学决策的参考时点，避免两边在不同时间运行而产生额外差异。模型调用和配额计时仍使用实际时间。模式 `learning_overview`、`learning_document`、`knowledge_graph` 会读取快照之外的记录或重新捕获状态，因此不纳入此协议；遇到它们会记录失败条件和缺失配对，不静默删题或假装完成。教师应在历史审核中拒绝不适用案例并说明原因。

原有不传 `--history-frozen` 的三方案协议保持冷启动含义，不能与本协议混合计算分母。两种协议的调用数上限仍显式记录；状态比较最多每题两次生成、两次审核。

## 输入来源和限制

历史包必须绑定已经冻结的课程/问题基线及每条题目的摘要。只允许两个明确的来源标签，同一个包不混用：

- `synthetic_scenarios`：教师审阅的假设学习情境，只能说明系统在设定状态下如何回答。
- `declared_deidentified_observations`：由负责人提供的脱敏观察，必须有非空使用许可记录引用，每条观察带事件级原始依据 SHA-256。工具只验证声明和结构，不能认证真人、来源真实性、同意程序或脱敏充分性；原始依据由负责人独立保存。

支持过去的正式作答结果声明 `grade`、已展示提示 `hint` 和复习计划 `review_schedule`。不直接导入任意掌握分值，不把复习自评写成测验成功；本版不导入误概念确认、反例判题或自述画像，相关组件的单独效应不在本协议中声称已验证。

每题最多 40 条观察，按实际发生时点升序，位于 `as_of` 前 365 天内；复习到期时间最多在 `as_of` 后一年。来源记录、历史分组不能跨开发集与测试集；同一 history_id 必须对应同一组观察。同一来源摘要不能在一个历史中重复计数，也不能在不同案例中对应矛盾事实。内容相同但换编号仍可能产生语义关联，人工仍需检查分组与泄漏，工具不保证样本独立性。

历史输入不接受姓名、邮箱、年龄、聊天正文、代码、完整业务 payload 等额外字段。工具不查询主库来补齐缺失项，不将来源摘要当成独立鉴真结果。

## 准备与审核

先完成[教师基线冻结](2026-10-18-teacher-baseline-workflow.md)，再生成空表。当前未满足第一步，不能用合成评审人代填通过。

```powershell
.venv/Scripts/python.exe backend/scripts/teacher_state_history.py --baseline output/plex-teacher-baseline-v1/frozen-review-v1.json --prepare output/teacher-history-draft-v1.json
```

空表中的 observations 为空，accepted、reviewer_id、reviewed_at、rationale、expected_adjustment 均为 null；工具没有自动编造历史或教师判断。

顶层保留 schema_version=1、status=pending_history_review 和 baseline_sha256。负责人填写 provenance、as_of；声明脱敏观察还要填写 permission_reference。reviewers 每项包含稳定 id 及三项明确声明：`declares_python_teaching_experience`、`declares_personal_review`、`declares_data_use_permission`。声明不等于身份认证。

每条 history 保留 case_id/case_sha256，填写 history_id、observations 及人工决定。默认同一问题族使用同一个 history_id；共享该编号的行需填写相同观察。使用不同历史情境时更换编号，不能跨数据划分复用同一历史。

每条观察严格包含以下字段，无关值填 null：

| 字段 | 内容 |
| --- | --- |
| id | 此历史内唯一编号 |
| kind | grade / hint / review_schedule |
| concept_id | 注册表中已有的规范 Python 知识点 ID，不用自由文本或别名 |
| at | 带时区的发生时间，不能晚于 as_of |
| correct、assisted | grade 填布尔值；其他类型均为 null |
| mode | hint 选择 explain_error/review_approach/next_step/pseudocode；其他类型为 null |
| due_at | review_schedule 填带时区的到期时间；其他类型为 null |
| source_sha256 | 脱敏观察必须填原始依据摘要；假设情境可以为 null |

教师对每题历史填 accepted=true/false、reviewer_id、实际 reviewed_at、rationale；接受时还要填写 expected_adjustment，说明该历史应怎样影响本题帮助，或为何不应改变。**这两个文字字段只用于人工审计，不进入模型输入。** 拒绝记录保留，不静默删行。至少每个数据划分有一个接受案例才允许冻结，最终样本数与拒绝数必须如实报告；此最低结构条件不是充分统计样本量。

```powershell
.venv/Scripts/python.exe backend/scripts/teacher_state_history.py --baseline output/plex-teacher-baseline-v1/frozen-review-v1.json --history output/teacher-history-draft-v1.json
.venv/Scripts/python.exe backend/scripts/teacher_state_history.py --baseline output/plex-teacher-baseline-v1/frozen-review-v1.json --history output/teacher-history-draft-v1.json --freeze output/teacher-history-frozen-v1.json
```

校验退出码 2 表示仍待审核/许可或缺少某组接受案例；1 表示格式、摘要、日期、分组等不合法；0 表示输入契约满足。冻结文件拒绝覆盖，修改问题、历史或审核决定后应创建新版本。

## 运行与评分

先只生成计划，不调用模型：

```powershell
.venv/Scripts/python.exe backend/scripts/evaluate_teacher_baseline.py --frozen output/plex-teacher-baseline-v1/frozen-review-v1.json --history-frozen output/teacher-history-frozen-v1.json --output output/state-eval-plan-v1 --split development
```

输入通过并确认调用预算后，使用新目录执行小批次：

```powershell
.venv/Scripts/python.exe backend/scripts/evaluate_teacher_baseline.py --frozen output/plex-teacher-baseline-v1/frozen-review-v1.json --history-frozen output/teacher-history-frozen-v1.json --output output/state-eval-development-v1 --split development --max-cases 3 --max-calls 12 --execute-model-calls
```

只有最后一个参数会产生付费模型调用；max-calls 是物理调用次数上限，不是货币预算。原有实际模型固定、无透明重试、实现摘要、素材摘要、输入冻结、随机顺序、失败保留和完整性清单继续生效。缺失任一条件不算完整配对。规则澄清或安全回退仍保留供评分；若两边均未调用模型，actual_model 为空，不能称为一次大模型效果实测。`complete_split` 表示本划分中**历史被接受的案例**是否全运行，manifest 同时保存原基线候选数和历史拒绝数，不代表所有原案例或所有学习状态均已覆盖。

将 blind-review.json 的副本及 approved-course-materials.json 交给评分者，保留原始结果。两种条件的评分行都展示同一份 history_context，评审者据此判断对这个学习者是否合适；不告知条件名称、模型名或预期调整标签。回答可能透露条件，不能宣称严格双盲。

沿用原[回答评分规则](2026-10-18-three-arm-teacher-evaluation.md)，填写后执行 `check_teacher_answers.py --run ... --reviews ... --report ...`。原始输入、历史、答案、来源均不能在评分副本里改写。

只有两边完整执行且每条都由声明评审者评分，才输出各条件汇总和 `paired_state_differences`：同题“可见－屏蔽”的描述性差值、有效配对数、N/A 配对数、不同历史分组数。泄题/过度拒答的正差表示风险更多，不能把所有正值都说成改善。

这些是序数评分和风险比例的描述性比较，不提供显著性或学习增益结论；相同历史分组中的题目不是独立样本。模型温度相同也不消除随机性；若需要重复实验，应提前确定重复次数并保留所有运行，不挑选最好的一次。误概念诊断准确性、长期状态估计质量及真实学生学习提升仍需要另外的人工依据和研究设计。

## 本轮状态

新增工具的历史、审核者和评分只在 pytest 临时夹具中构造；它们不是正式数据。当前真实教师基线仍未冻结，本轮不创建已审核历史包、不调用外部模型、不读取或写入业务学习记录，也不报告个性化提升指标。真实 Docker、浏览器、教师评测与试用的阻塞仍按[完成度审计](../2026-10-18-plex-intelligence-completion-audit.md)处理。
