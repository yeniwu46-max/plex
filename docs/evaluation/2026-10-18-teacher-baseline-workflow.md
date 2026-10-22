# PLEX 教师标注基线：填写、校验与冻结

状态：工程工具完成，**人工标注尚未开始**。准备包包含 120 条 AI 辅助编写的合成候选，不包含真实学生对话，也没有预填教师结论、正确答案或课程相关性等级。不能把候选数量写成「120 条教师金标准」或当作已经完成的效果实验。

## 交给教师的材料

运行根目录 `.venv/Scripts/python.exe backend/scripts/prepare_teacher_baseline.py`，默认创建 `output/plex-teacher-baseline-v1/`。已存在的目录不会覆盖；再次生成请选择新目录与版本。

| 文件 | 用途 |
| --- | --- |
| `review-pack.md` | 人可读的 120 条候选；含题面、代码、拟分组与待验证边界 |
| `cases.json` | 固定候选正文、代码、知识点和拟划分；修改会使原审核摘要失效 |
| `reviews.json` | 需要人工填写的唯一标注表；所有 accepted 初始为 null，reviewers 初始为空 |
| `corpus.json` | 教师批准用于本次评测的课程材料副本；初始为空 |
| `README.md` | 操作入口与完成条件，由仓库说明复制生成 |

20 个知识点，每个含直接提问、概念困惑、算法验证、调试、推演各 1 条，再加 1 条缺课程证据或上下文冲突案例。合计 100 条常规问题与 20 条边界问题；每类边界各 10 条。

同一知识点的 6 个变体放在同一分组，目前拟为开发集 96 条、测试候选 24 条。这是减少明显重叠的分组规则，**不保证语义无泄漏或真实课堂代表性**：仍含共同写作模板，需教师审查重复性、难度与措辞。拟测试分组可见，因此不声称是对开发者保密的测试；正式冻结前应由负责评测的人检查分组，冻结后不得据其结果反复调参。

所有代码均未标为执行验证。debugging 特意包含异常、逻辑错误和不终止循环；不要直接在宿主机批量执行。需要实测轨迹时，使用恢复后已验收的隔离执行器并单独留存报告。教师手工推演不应被记成已经真实运行。

## 填写顺序

1. 教师先阅读题目，判断语义是否清楚、是否符合 Python 课程、需要什么上下文。遇到不清晰、不合理或重复题，accepted=false，并写理由；不要为凑足数量勉强接受。
2. 将有权用于评测的课程材料放入 corpus.json，记录编号、版本、来源及完整正文摘要。不要直接导出私人聊天、账号、密钥或未经同意的学生代码。
3. 在 reviewers 登记教师自选的固定代号，不要求邮箱或身份证明。填写教学经历和亲自审阅声明。离线工具无法认证真人身份，研究使用仍需负责人保存实际审核责任记录。
4. 按案例填写 reviews：是否接受、审阅时间、理由、真实意图、依据是否充足、预期教学动作、应覆盖的要点、课程证据相关性。**proposed_intent 只是草稿标签，不应自动抄成 gold_intent。**
5. 运行检查；补齐错误后再冻结。拒绝案例保留在文件中，不静默删除，不被计入可评测案例数。需要修改题目时创建新版本并重新标注，不能绕过摘要检测沿用旧结论。

常规案例建议先由一位教师独立审阅，再由另一位教师抽样复核争议和留出案例。当前工具每题记录一个最终审核；它不实现双盲、多评审投票或一致性系数，也不声称单次人工标注已经具有高可靠度。争议须在冻结前由人处理并在 rationale 说明。

## 课程材料格式

corpus.json 保持 schema_version=1，documents 为列表。每项必须提供：

| 字段 | 要求 |
| --- | --- |
| id | 稳定编号，英文字母、数字、点、横线、下划线，最多 80 字符 |
| version | 大于 0 的整数；内容变化后增加版本 |
| title | 最多 300 字符 |
| content | 本次评测材料完整正文；最多 200,000 字符 |
| content_sha256 | content 的 UTF-8 字节 SHA-256，小写十六进制；不能用文件名替代 |
| source_reference | 能定位原课程材料的说明，最多 1,000 字符 |
| approved_for_evaluation | 仅在确认有权使用后填写 true |

可在可信 Python 环境中用 `hashlib.sha256(content.encode('utf-8')).hexdigest()` 计算正文摘要；该操作只做摘要，不执行正文。JSON 文件最多 8 MiB，最多 1,000 个材料；不接受重复对象键或 NaN。

## 人工标注字段

reviewers 每项为 id、declares_python_teaching_experience=true、declares_personal_review=true。工具校验声明，**不把声明当成独立认证的人类评审证据**。

每条 review 已有 case_id/case_sha256，保留原值。人工填写：

| 字段 | 要求 |
| --- | --- |
| reviewer_id | 对应 reviewers 中的稳定代号 |
| reviewed_at | 带时区的实际审阅时间，如 YYYY-MM-DDTHH:MM:SS+08:00；不能填未来时间 |
| accepted | true 接受该候选；false 拒绝；null 尚未审阅 |
| rationale | 接受/拒绝及边界判断依据，最多 3,000 字符 |
| gold_intent | direct_question / concept_confusion / algorithm_validation / debugging / algorithm_trace / needs_context / out_of_scope |
| answerability | supported / needs_context / no_course_evidence / out_of_scope |
| expected_action | explain / locate_error / check_reasoning / next_step / pseudocode / trace / ask_context / limited_evidence |
| expected_response_points | 教师列出的 1–12 个必要要点，不直接当成学生端输出 |
| evidence | 最多 20 个课程材料引用；每项 document_id、version、content_sha256、relevance |

relevance 为整数 1、2、3：1 为背景相关但不足以直接支撑关键结论；2 为支撑部分关键结论；3 为直接支撑本题关键结论。只是该次人工相关性等级，不是准确概率。不要把被复制的同一段材料当作多份独立依据。

- supported 必须至少有一个版本/正文摘要匹配的材料引用。
- needs_context 必须选择 ask_context；缺少必要题目或代码时，不编造上下文。
- no_course_evidence/out_of_scope 选择 limited_evidence 或 ask_context，不编造课程来源。
- accepted=false 仍需审阅者、时间和理由，其他金标准字段不计入评测。所有候选都需被明确处理；最终接受数如不足 120，报告实际数量。

## 校验与冻结命令

在仓库根目录运行：

```powershell
.venv/Scripts/python.exe backend/scripts/check_teacher_baseline.py --pack output/plex-teacher-baseline-v1 --report output/plex-teacher-baseline-v1/status.json
```

退出码 0：全部审核字段及覆盖门槛满足；2：结构有效但仍有待审或覆盖缺口；1：结构、摘要、证据、时间或标签不合法。退出码 2 不是模型故障，不能通过填充假评审者清除。

开发与拟测试两组都须保留五种常规意图，以及缺课程证据、上下文冲突两类边界。若拒绝了一个类别的全部候选，先修订案例新版本并重新审阅，不能只删掉难例来获得“通过”。

完成后由负责人执行：

```powershell
.venv/Scripts/python.exe backend/scripts/check_teacher_baseline.py --pack output/plex-teacher-baseline-v1 --freeze output/plex-teacher-baseline-v1/frozen-review-v1.json
.venv/Scripts/python.exe backend/scripts/check_teacher_baseline.py --verify output/plex-teacher-baseline-v1/frozen-review-v1.json
```

冻结文件包括候选、课程材料、人工声明/标注、覆盖报告与整体 SHA-256；不能覆盖已有文件。修改任一部分会使校验失败。它只能证明文件完整性和声明字段符合契约，不能证明人类真的审阅或课程材料内容正确。

## 之后如何评测

冻结只是输入准备，**不会调用模型，也不输出 Recall、准确率或教学增益**。既有 `evaluate_knowledge_retrieval.py` 目前仍消费单独的合成工程回归集，不能把它的数值改名为这份教师基线成绩。

已提供独立的[三方案评测与回答评分工具](2026-10-18-three-arm-teacher-evaluation.md)：通过教师冻结校验后，在临时数据库和固定模型配置下运行直接问模型、当前课程 RAG、真实小 E 辅导链路，并输出待人工评分包。当前只覆盖没有学习历史的新用户场景，不代表状态个性化消融；实际教师输入尚未就绪，因此没有执行正式质量对照。

缺上下文样本评教学动作，不能因为检索到了相似文字就当作可回答。教师需盲评实际回答的正确性、来源支持、动作适配、可执行下一步和泄题情况。真实推演仍要核对隔离执行证据。

当前 120 条为合成候选、0 条教师实审、0 次正式基线质量实验。课堂约 20–30 人自愿试用、教师题库发布审核、模型账单对账及浏览器视觉验收仍是其他未完成的事项。准备包默认位于 Git 忽略的 output 中；源码与说明可纳入将来的授权提交，填过的教师资料和材料副本不要自动提交。
