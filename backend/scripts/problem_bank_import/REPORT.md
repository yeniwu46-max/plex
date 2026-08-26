# 题库导入与展示 —— 交付报告

本报告覆盖需求中的两个任务：

- **任务1**：清洗旧题库系统（类 HydroOJ/Mulberry）导出的 MySQL dump，设计新表结构并生成可导入的 SQL。
- **任务2**：基于任务1的标准化字段，提供后端 API 与前端预览页面。

原始 dump 位于 `_incoming_data/learning_core_groups_masked_normal.sql`（约 54MB，已在 `.gitignore` 中排除，不进入 git 历史）。所有清洗脚本位于本目录 `backend/scripts/problem_bank_import/`。

---

## 一、数据量对比（清洗前 → 清洗后）

| 表 | 原始行数 | 保留行数 | 主要过滤/去重原因 |
| --- | ---: | ---: | --- |
| `problem` | 70 | 70 | 本次 dump 中 `status` 全部为 1、`remove_time` 全部为 0，无题目被状态/软删除过滤；重复标题检测命中 0 条 |
| `solution` | 28,605 | 26,756 | 见下表明细 |
| `gen_hint` | 13,731 | 0（未导入） | 非本次任务重点，未建表导入；其中 1,137 条引用了被提交记录清洗环节剔除的 `solution_id`（外键悬空，见下文说明） |

`solution`（→ `problem_submissions`）清洗明细：

| 处理项 | 数量 | 说明 |
| --- | ---: | --- |
| 原始行数 | 28,605 | |
| 内容为空/空白（丢弃） | 5 | `content` trim 后为空字符串，无法展示/评分，列入人工核对清单确认 |
| 完全重复提交（丢弃） | 1,844 | 同一 `(user_id, problem_id, content)` 三元组的重复投递，保留最早一次 `create_time` 的记录，其余视为无信息量的重复点击 |
| 引用被过滤 problem（丢弃） | 0 | 本次 dump 没有 problem 被过滤，因此没有孤儿提交 |
| **最终导入** | **26,756** | |

> `problem.status`：全表扫描后确认该 dump 中仅出现值 `1`，语义为"启用"；`remove_time`：全表均为 `0`，语义为"软删除时间戳，0 = 未删除"。两条过滤规则均已在脚本中实现（`clean_and_transform.py::clean_problems`），本次 dump 未触发实际丢弃，但保证了对未来增量导入的健壮性。

---

## 二、脏数据分类与处理方式

| 脏数据类型 | 典型样例 | 处理方式 |
| --- | --- | --- |
| `{[...]}` 自定义高亮标记 | `{[Hello, Rabbit!]}` | 正文（description）中转换为 Markdown 加粗 `**Hello, Rabbit!**`；样例值（input/output）中直接去除标记只保留纯文本，因为样例需要"一键复制"，不应带 Markdown 符号 |
| HTML 标签混排 | `<sup>2</sup>`、`<b>...</b>`、`<hr />`、`<a href="...">` | `<sup>` 转 `^`（如 `x<sup>2</sup>` → `x^2`）；`<b>` 转 Markdown `**`；`<hr />` 作为多组样例的分隔符识别后拆分为独立 `samples[]` 条目；`<a href>` 保留链接文本、去除标签 |
| 代码块记号 ` ```python ... ``` ` | 描述正文中夹带的代码块 | 保留为 Markdown 代码块（前端 `MarkdownRenderer` 原生支持渲染+高亮），不做进一步处理 |
| 全角/半角混用标点 | 中文描述里样例数字被误标全角（如 "５" 应为 "5"） | 正文级别的中文全角标点（，。！？：；""''）保留；但样例 input/output 内的数字、程序关键字统一转为半角，避免例如 `input()` 读到全角数字导致语义错误 |
| 首尾空白/连续空格/全角空格/Tab | `group.description` 尾随 `\t`、描述行首多个空格 | 统一 `strip()` + 折叠连续空白为单个空格（正文用换行分段场景除外）；全角空格 `\u3000` 归一为半角空格 |
| description 占位符 `'English Description'` | `problem.id` 83～150 附近多条 | 判定为"英文原文缺失"，`description_en` 置为 `NULL`，并计入人工核对清单，不臆造英文翻译 |
| 空样例 `{[]}` | `problem.id` 56/57/89 等 | 若中/英文描述任一侧能解析出非空样例则采用该侧（如 EN 为空、CN 有值则用 CN，反之亦然）；两侧都为空则转入沙箱真实执行参考答案补齐（见"九、2026-07-30 增强篇"第2项），仍无法安全生成则计入人工核对清单，不臆造样例数据 |
| 提交代码为空 | `solution.content` 为空/纯空白 | 丢弃（无法展示/评分），计入人工核对清单 |
| 完全重复提交 | 同一用户对同一题目重复提交完全相同的代码 | 按 `(user_id, problem_id, content)` 去重，保留最早一次 |
| 输入格式缺失但代码需要 `input()` | 参考答案里调用了 `input()`，但描述正文没有明确的"输入格式"段落 | 无法可靠地从正文反推格式说明，不生硬留空造假，而是计入人工核对清单，交由人工补充 |

以上规则全部在 `text_cleaning.py`（纯函数：`clean_body_text`、`clean_sample_value`、`parse_description`、`split_input_output_format`、`extract_notes`）与 `clean_and_transform.py` 中实现，可重复运行、结果确定（幂等）。

### `solution.output` 编码格式推断依据

原始 `output` 字段形如：

```
Tom$$Hello, Tom!$$S##Mike$$Hello, Mike!$$S##Lily$$Hello, Lily!$$S##
```

通过枚举含多个 `##` 分隔符的样本，并与 `test_success`/`compile_success`/`status`/`points`/`total_points` 交叉核对，推断格式为：每个测试点一个 `<回显/标签>$$<实际输出>$$<判定>##` 块拼接，`<判定>` 取值 `S`（Success，通过）或 `F`（Fail，未通过）。验证依据：

- 16,718 条记录能解析出至少一个 `$$...##` 块；其中 89.32% 的"块数"与 `total_points`（应有测试点数）一致，95.13% 的"S 块数"与 `points`（得分测试点数）一致，误差主要来自极少数测试点权重不均的题目。
- 剩余 11,840 条无法解析出 `$$...##` 块的记录，`status` 分布为 `CE: 8175, TE: 2262, AC: 1403`——多数是编译失败（无测试点可跑，`output` 是原始 Python Traceback 文本），保留在 `raw_judge_output` 字段供审计，不强行拆分成虚假的测试点结果。

### `solution.status` 全量枚举与语义

对 28,605 行做 `Counter(status)` 全量统计，结合 `returncode`/`error_name` 交叉表，得到 4 个互斥取值：

| status | 语义 | 判定依据 |
| --- | --- | --- |
| `AC` | Accepted，全部测试点通过 | `returncode == 0`，且无 `error_name` |
| `TE` | Test Error（运行成功但未全部通过 / 超时） | `returncode == 0`（未通过部分测试点）或 `returncode == -9`（推测为强制终止/超时，207 条） |
| `CE` | Compile Error（含 Python 的"编译期"语法/名称/类型等静态错误） | `returncode == 1`，且 `error_name` 必为 `SyntaxError`/`NameError`/`TypeError`/`IndentationError`/`ValueError`/`EOFError` 等之一（Python 无真正编译期，这里把提交后立即报错、未产生任何测试点输出的情况统一归为 CE，与旧系统 UI 展示习惯保持一致） |
| `UE` | Unknown/运行时未知错误 | `returncode == -1`，仅 47 条，可能是评测沙箱异常退出 |

---

## 三、新表结构

### `problems`（标准题目表，70 行）

关键字段：`id`（复用旧 problem.id）、`problem_no`（A001 风格题号）、`concept`/`concept_group`、`title_en`/`title_cn`、`background`（本次数据源无背景字段，预留 NULL）、`description_en`/`description_cn`（已清洗 Markdown 正文）、`input_format_en`/`output_format_en`/`input_format_cn`/`output_format_cn`、`samples_json`（`[{input, output}]` 结构化数组）、`notes_json`（字符串数组）、`difficulty`/`level`/`topic`、`reference_answer`、`template`、`legacy_problem_name`/`legacy_author_user_id`、`is_active`、`created_at`/`updated_at`。

### `problem_legacy_quest_map`（题目↔旧 quest 关联，保留旧系统课程编排信息）

字段：`problem_id`、`legacy_quest_id`、`legacy_quest_title_cn`、`required`、`sort_order`。

### `problem_submissions`（标准提交记录表，26,756 行）

关键字段：`id`（复用旧 solution.id）、`problem_id`、`legacy_user_id`/`legacy_username`/`legacy_student_name`/`legacy_group_id`/`legacy_group_name`（旧账号不对应当前 PLEX 学生账号，仅作展示用途）、`code_content`、`status`、`is_accepted`（`status == 'AC'` 的布尔便捷字段）、`compile_success`/`test_success`、`score_points`/`score_total`/`score_percent`（OI 标准评分，见下）、`test_case_results_json`（解析后的分测试点结果）、`raw_judge_output`（无法解析时的原始文本，审计用）、`exec_time_ms`（毫秒）、`exec_memory_kb`（KB）、`time_spent_seconds`（秒）、`self_confidence`、`legacy_error_name`/`returncode`、`legacy_prev_solution_id`（保留旧的重试链）、`submitted_at`。

三张表均已在 `schema.sql` 中定义（`utf8mb4`/`utf8mb4_unicode_ci`，为 `problem_id`/`legacy_user_id`/`status`/`problem_no` 等常用查询字段建了索引，每个字段均有注释），并同步建模为 SQLAlchemy model：`backend/app/models/problem_bank.py`（`Problem`、`ProblemLegacyQuestMap`、`ProblemSubmission`），通过 Alembic 迁移接入：`backend/migrations/versions/20260730_0009_problem_bank.py`。

**OI 标准评分依据**：旧系统的 `solution.points`/`solution.total_points` 本身就是"按测试点通过比例给分"（而非简单 0/100），验证见上文"输出编码格式推断依据"一节的块数/得分交叉核对。因此 `score_percent = round(points / total_points * 100, 1)` 直接复用原始字段，未做臆造折算；当 `total_points` 为 0/NULL 时 `score_percent` 置为 `NULL`（多见于 `CE` 编译失败、尚未跑出任何测试点的记录）。

**时间单位确认**：`time_spent`（学生答题耗时）样本值集中在个位数到几百之间，与"秒"量级吻合，字段重命名为 `time_spent_seconds` 并保持数值不变；`test_time`（评测执行耗时）与 `test_space`（评测内存占用）分别重命名为 `exec_time_ms`/`exec_memory_kb`，单位判断依据是典型 OJ 沙箱惯例（时间以毫秒为粒度、内存以 KB 为粒度）且数值分布符合预期量级，已在字段名中显式标注单位，避免歧义。

---

## 四、题号命名规则

字母分组映射（`concept` → `concept_group`）：

| concept | 分组字母 |
| --- | --- |
| Basics | A |
| Operators | B |
| Conditionals | C |
| Loops / For Loops / While Loops | D（同一教学阶段的不同粒度标签，合并为一组） |
| Functions | E |
| DataTypes | F（需求示例未覆盖，按"基础数据类型先于高级类型"的课程顺序补充在 Functions 之后，属本次自主设计决策） |
| HighTypes | G（同上） |

组内编号：按 `(create_time, id)` 升序从 1 开始，三位数补零（如 `A001`），确保脚本重跑幂等（`assign_problem_numbers`，见 `clean_and_transform.py`）。

实际分布（本次 70 题）：A=8, B=11, C=8, D=26, E=11, F=5, G=1。

标题沿用策略：`title_en`/`title_cn` 直接复用原 `title`/`cn_title` 字段（仅做空白/标点清洗），未做覆盖性改写——原标题语义清晰（如"打招呼""HelloRabbit"），不需要重新概括。

---

## 五、生成的文件

### SQL（可直接 `mysql -u USER -p DB < 文件` 导入）

- `backend/scripts/problem_bank_import/schema.sql` —— 三张表建表 DDL
- `backend/scripts/problem_bank_import/output/data.sql` —— 合并版 INSERT（约 13.8MB）
- `backend/scripts/problem_bank_import/output/data_problems.sql`
- `backend/scripts/problem_bank_import/output/data_problem_legacy_quest_map.sql`
- `backend/scripts/problem_bank_import/output/data_problem_submissions.sql`（约 13.7MB）

以上 `output/` 目录内容体积较大，已加入 `.gitignore`，不进入 git 历史；`schema.sql`、脚本源码、`manual_review.md`、本报告均正常入库。

### 本地 SQLite 导入（开发联调用）

`backend/scripts/problem_bank_import/load_sqlite.py` 直接通过 SQLAlchemy 写入 `backend/instance/learning_system.db`，脚本内部先按主键 `id` 做存在性检查再插入/跳过，可重复运行不产生重复数据。

### 清洗脚本与中间产物

- `_dump_reader.py` —— mysqldump 文本解析器（提取 `CREATE TABLE`/`INSERT` 行，处理转义）
- `inspect_dump.py` / `analyze_quality.py` / `analyze_quality2.py` —— 探索性分析脚本（表结构抽样、脏数据统计、`output` 编码格式与 `status` 语义推断）
- `text_cleaning.py` —— 文本清洗纯函数库
- `clean_and_transform.py` —— 主清洗流水线，产出 `output/problems.json`、`output/problem_legacy_quest_map.json`、`output/problem_submissions.json`、`output/stats.json`、`manual_review.md`
- `generate_sql.py` —— 由 JSON 中间产物生成上述 `.sql` 文件
- `load_sqlite.py` —— 由 JSON 中间产物写入本地 SQLite

---

## 六、人工核对清单摘要

完整清单见 [`manual_review.md`](./manual_review.md)，经 2026-07-30 增强篇的样例沙箱补齐后，最终合并为 **44 条**（`backend/scripts/problem_bank_import/finalize_manual_review.py` 合并清洗阶段、背景生成阶段两处产出，去重后写入）：

- `problem` 表 39 条：
  - 17 条"description(英文) 为占位符 'English Description'，原文缺失"（比初版报告的 13 条更精确，重新全量扫描后的口径，id=83~150 附近）
  - 14 条"参考答案调用了 `input()`，但正文没有可提炼的输入格式说明"
  - 7 条"样例原本缺失，已通过本地沙箱真实执行参考答案自动生成一条样例"——**这 7 条已不是"待处理"而是"待复核"**：样例已可用（真实执行结果），只是建议人工确认是否覆盖了题意的全部边界情况
  - 1 条"题目描述提到用户输入，但参考答案代码完全不读取任何输入"（题面与代码行为不一致，id=26《切开那个数》）
- `solution` 表 5 条：提交代码为空/空白，已从导入数据中剔除，仅登记备查
- 题目背景故事生成阶段：0 条（70 道题全部由 AI 成功生成，无需转人工，见增强篇第1项）

所有条目均标注了原始表名+主键 id、问题描述与处理建议（保留/丢弃/需人工补充的具体字段），未做任何"猜测式"自动补全。

---

## 七、任务2：新增文件清单

### 后端

- `backend/app/routes/problem_bank.py` —— 新增路由，注册进 `backend/app/routes/__init__.py`，前缀 `/api/v1/problem-bank`，均需 `@jwt_required()` + `@role_required('teacher', 'admin')`：
  - `GET /problems` —— 题目列表（支持 `concept_group`/`keyword`/`tag` 过滤，`tag` 为 2026-07-30 增强篇新增）
  - `GET /problems/<id>` —— 题目详情（结构化字段，见下，含增强篇新增的 `has_english`/`star_difficulty`/`tags`）
  - `GET /problems/<id>/stats` —— **新增**：标题统计条（提交数/通过数/时间限制，支持 `legacy_group_id` 切换班级口径）
  - `GET /tags` —— **新增**：标签列表（按 `tag_type` 分组）
  - `GET /problems/<id>/submissions` —— 该题提交记录列表（支持 `legacy_user_id`/`limit` 过滤，不含代码正文）
  - `GET /submissions/<id>` —— 单条提交详情（含完整代码 `code_content`）
- `backend/app/services/problem_bank.py` —— `ProblemBankService` 服务层，新增 `list_tags`/`get_problem_stats`
- `backend/app/models/problem_bank.py` —— `Problem`/`ProblemLegacyQuestMap`/`ProblemSubmission`/`ProblemTag`/`ProblemTagMap` model，已注册进 `backend/app/models/__init__.py`
- `backend/migrations/versions/20260730_0009_problem_bank.py` —— 初版 Alembic 迁移
- `backend/migrations/versions/20260730_0010_problem_bank_enhancements.py` —— 增强篇 Alembic 迁移（新增列 + 标签两张表）

题目详情响应字段：`background`、`background_source`、`description_en`/`description_cn`、`has_english`、`input_format_en`/`output_format_en`/`input_format_cn`/`output_format_cn`、`samples`（`[{input, output}]`，纯文本可直接复制）、`samples_source`、`notes`（字符串数组）、`problem_no`、`title_en`/`title_cn`、`concept`/`concept_group`、`difficulty`/`level`/`star_difficulty`、`time_limit_ms`/`time_limit_is_default`、`tags`（`[{id, code, label, tag_type, color}]`）。

提交记录响应字段：`is_accepted`、`status`、`score_percent`/`score_points`/`score_total`、`exec_time_ms`、`exec_memory_kb`、`time_spent_seconds`、`legacy_student_name` 等；详情接口额外返回 `code_content`、`test_case_results`、`raw_judge_output`。

### 前端

- `frontend/src/api/problemBank.ts` —— API 封装，新增 `fetchProblemBankTags`/`fetchProblemStats`，`ProblemDetail`/`ProblemSummary` 类型补充增强篇字段
- `frontend/src/components/problemBank/CopyableBlock.vue` —— 通用"带复制按钮的文本/代码块"组件
- `frontend/src/components/problemBank/ProblemDetailView.vue` —— 题目详情展示（标题行含星级+语言切换、统计条、标签区、背景/描述/输入输出格式/样例/说明，样例块可一键复制）
- `frontend/src/components/problemBank/StarRating.vue` —— **新增**：1-5 星难度展示（支持 `compact` 精简模式）
- `frontend/src/components/problemBank/ProblemTagChips.vue` —— **新增**：标签 chips 展示（`topic` 标签可折叠"展开/隐藏算法标签"），点击标签 emit 事件
- `frontend/src/components/problemBank/ProblemStatsBar.vue` —— **新增**：标题右侧统计条（提交/通过/时间限制 + 旧班级口径下拉选择）
- `frontend/src/components/problemBank/SubmissionCodeModal.vue` —— 提交记录详情弹窗（等宽字体展示代码、复制按钮、测试点结果）
- `frontend/src/views/ProblemBankPreviewView.vue` —— 教师端预览页，整合题目列表（含星级、标签筛选提示条）+ 详情 + 提交记录列表 + 代码弹窗
- 路由：新增 `/teacher/problem-bank`（`frontend/src/router/index.ts`），**这是本次新增的独立预览入口，尚未挂接到正式侧边栏导航**，仅在 `TeacherSidebar.vue` 的 `TeacherNavKey` 类型中占位（不渲染导航按钮），后续挂载位置由使用方决定。

---

## 八、本地验证步骤

### 后端数据 + API

1. 已用 `load_sqlite.py` 将清洗后数据写入 `backend/instance/learning_system.db`（70 条 `problems`，26,756 条 `problem_submissions`）。
2. 启动后端：`cd backend; python run.py`（默认监听 `127.0.0.1:5100`）。
3. 用教师账号登录：`POST /api/v1/auth/login`，`{"username": "teacher001", "password": "teacher123"}`，取返回的 `access_token`。
4. 依次调用并已实测通过（200 响应）：
   - `GET /api/v1/problem-bank/problems` → 70 条，含 `problem_no`（如 `A001`）
   - `GET /api/v1/problem-bank/problems/{id}` → 结构化详情（背景/描述/格式/样例/说明）
   - `GET /api/v1/problem-bank/problems/{id}/submissions` → 提交列表
   - `GET /api/v1/problem-bank/submissions/{id}` → 含完整代码的提交详情

   抽查全部 70 题的样例解析结果：初版有 7 题 `samples` 为空数组，2026-07-30 增强篇已通过沙箱真实执行参考答案全部补齐（见增强篇第2项），当前 70 题 `samples_json` 均非空。

### 前端页面

1. `cd frontend; npm run dev`（默认 `http://localhost:5180`）。
2. 用教师账号（`teacher001` / `teacher123`）登录后，浏览器打开 `http://localhost:5180/teacher/problem-bank`，可看到题目列表（题号+星级）→ 选中题目查看结构化详情（标题行含星级、语言切换按钮、统计条；下方标签 chips；背景故事；描述/格式/样例/说明）→ 点击标签跳转筛选该标签下的题目列表 → 切换到提交记录 Tab → 点击一条提交弹出代码弹窗（含复制按钮）。
3. 全部新增/修改的前端文件均已通过 Vite dev server 的模块转换验证（请求均返回 200，无编译期语法错误），且 `npx vue-tsc --noEmit` 对新增文件本身零报错。
4. 后端增强接口已用 `backend/_smoke_test2.py` 脚本实测（教师账号登录 → `GET /problems?concept_group=D` → `GET /tags` → `GET /problems/{id}` 校验 `has_english`/`star_difficulty`/`background`/`tags` → `GET /problems/{id}/stats` 校验按班级切换的提交/通过数 → `GET /problems?tag=concept:D` 校验标签筛选），全部返回预期结果。

> 说明：仓库现存的 `npm run build`（`vue-tsc -b` 类型检查）会因 `frontend/src/views/StudentGrowthView.vue` 中一处与本次改动无关的既有语法错误（字符串未闭合）而失败，该问题在改动前已存在，超出本次任务范围，未做修复；已通过上述 dev server + `vue-tsc --noEmit` 方式确认新增/修改文件自身没有引入新的编译错误。

---

## 九、2026-07-30 增强篇：六项功能补充

在任务1/任务2交付基础上，用户追加了 6 项增强需求。以下逐项说明实现方式、口径依据与取舍理由；涉及的新增脚本均在 `backend/scripts/problem_bank_import/` 下，可重复运行、幂等。

### 1. 题目背景故事化生成——"小E"人设

- **人设复用**：搜索代码库确认"小E"是 `backend/app/services/messenger_chat.py` 里已定义的驿站助手人设（`ASSISTANT_SYSTEM_PROMPT`），本次背景生成 prompt（`generate_backgrounds.py::ASSISTANT_PERSONA`）复用同一身份设定与语气，不另起人设。
- **连续故事设计**：按 `concept_group`（A~G 共 7 组）分别设计了一个"世界观"（如 D 组"循环回廊"、E 组"魔法工坊"），组内题目按 `problem_no` 顺序生成"第 N/总数 章"，每章 prompt 都会附上"上一章摘要"要求承接情节，AI 与模板兜底路径都遵循同一叙事结构。
- **AI 调用链**：复用现有 provider 链约定（讯飞星火 → 讯飞星辰 Agent → DeepSeek → 规则模板兜底），实现见 `generate_backgrounds.py::_ai_chain`，分别调用 `IflytekSparkService`/`XfyunAgentService`/`agents.llm_client.chat_text`（与 `pedagogical_resource.py`、`ai_question_generator.py` 使用的是同一套底层客户端）。
- **实际生成结果**：讯飞星火与星辰 Agent 在当前网络环境下连接失败（`SSLError`，与此前 `check_ai_channels.py` 健康检查的 `blocked_credential_missing`/网络受限现象一致），DeepSeek 链路可用，**70 道题全部由 DeepSeek 成功生成**（`background_source = 'ai:deepseek'`，0 道走规则模板兜底）。若未来 DeepSeek 也不可用，`_template_chapter` 规则兜底仍能保证同一 `concept_group` 内的模板故事按世界观场景轮换、维持连续性（不会退化成互不相关的独立段子）。
- **字段与脚本**：`problems.background`（`TEXT`，迁移前已是 `TEXT` 类型，无需变更列类型）、新增 `problems.background_source`（记录来源，`ai:spark`/`ai:xfyun_agent`/`ai:deepseek`/`template`，仅供审计，不面向学生展示）。脚本 `generate_backgrounds.py` 支持 `--force`（强制重新生成全部）与默认的"仅生成缺失"两种模式，重跑时会先加载 `output/problems.json` 中已有的 `background`/`background_source` 予以保留（幂等）。

### 2. 15 道缺样例题目核实与智能补齐

- **口径核实**：重新用脚本精确统计后确认——初版报告的"7 题缺样例"统计口径是"**中英文描述都解析不到样例**"；这次用户复核发现的"15 题"实际是"**恰好一侧语言（几乎都是英文）解析不到样例，另一侧（中文）有**"的情况（例如英文描述是占位符或样例骨架为空 `{[]}`，但中文描述完整）。两者不重叠、口径不同：`both_missing=7`，`one_sided_missing=15`，合计 22 题至少一侧缺样例。由于最终对外只暴露一份共享的 `samples_json`（清洗时已实现"优先取有值的一侧"逻辑，见 `text_cleaning.py`），这 15 题的**实际展示效果本就完好**（自动走中文样例），不需要额外处理；真正需要补救的只有 `both_missing` 的 7 题。
- **沙箱补齐方式**：新增 `sandbox_exec.py`，对这 7 题的 `reference_answer`：
  - 先用 AST 解析（Python）静态检查代码不含 `os`/`subprocess`/`socket`/`open`/`eval`/`exec` 等风险调用，拒绝不安全代码；
  - 从题目描述里用正则提炼"输入："后的示例值作为构造输入（找不到则退化为固定探测值 `'PLEX'`）；
  - Python 用 `subprocess` + `-I`（隔离模式）+ 5 秒超时执行；Java 检测到 `public class`/`System.out.println` 特征后用 `javac`+`java` 编译执行（编译 15 秒/运行 5 秒超时）；
  - 取真实 stdout 作为样例输出，**不存在任何编造成分**——若执行失败/超时/无法识别语言/判定不安全，一律不生成样例，转入 `manual_review.md` 并写明卡在哪一步（`unsafe_python_rejected`/`python_execution_failed_or_timeout`/`unrecognized_language` 等具体原因）。
- **实际结果**：7 题全部成功执行并生成样例（6 题 Python 执行成功、1 题 Java 编译执行成功），**0 题转人工**；但这 7 条仍登记进 `manual_review.md`（标注为"建议复核"而非"待处理"），因为沙箱只生成 1 组样例，不能保证覆盖题目的全部边界情况，建议人工二次确认。补齐结果写入 `problems.samples_json`（格式与原有 `[{input, output}]` 一致），来源记录在新增字段 `problems.samples_source`（`parsed_from_description` 63 题 / `executed_reference_answer:python_executed_ok` 6 题 / `executed_reference_answer:java_executed_ok` 1 题）。

### 3. 洛谷风格标签系统

- **新增表**：`problem_tags`（标签字典：`code`/`label`/`tag_type`/`color`/`sort_order`）、`problem_tag_map`（题目↔标签多对多，`(problem_id, tag_id)` 唯一约束），DDL 见 `schema.sql`，ORM 见 `backend/app/models/problem_bank.py::ProblemTag`/`ProblemTagMap`。
- **标签维度**（刻意不生成图2里"年份/赛事"这类不存在的比赛信息，替代设计如下）：
  - `concept`（知识点分组，复用 `concept_group`，7 个，如"循环""函数"）——每题固定 1 个；
  - `topic`（细粒度算法/实现方式标签，规则匹配代码特征 + 描述关键词得出，6 种命中：字符串处理/数学运算/递归/字典/嵌套循环/嵌套条件）——0~N 个，`generate_tags.py::_topic_tags_for` 通过正则匹配 `reference_answer` 源码特征（如 `def f(...): ... f(...)` 判定递归、缩进层级判定嵌套循环/条件）识别，比单纯关键词匹配更可靠；
  - `difficulty`（难度分档，与第4项的 1-5 星一一对应，5 个）——每题固定 1 个；
  - `source`（来源说明，8 个，取自旧系统 `quest` 章节真实标题，如"来源：受伤的兔子""来源：可怕的老虎"）——**这是图2"年份/赛事"位置的替代设计**：我们的题库不是真实竞赛题，编造 NOIP/年份信息会误导用户，改为如实标注该题在旧系统课程编排里所属的真实章节名称，同样起到"这道题从哪儿来"的说明作用，但不失实。
- **生成结果**：26 个标签（7 concept + 5 difficulty + 8 source + 6 topic），284 条题目-标签关联；`generate_tags.py` 目前全部走规则匹配（未调用 AI，规则命中率已足够，避免不必要的 AI 调用开销），预留了接入 AI 辅助打标的位置（复用第1项的 `_ai_chain`）但本次判断规则已够用故未启用。
- **后端接口**：`GET /api/v1/problem-bank/tags`（标签列表，按 `tag_type` 分组返回）、`GET /api/v1/problem-bank/problems?tag=<code>`（按标签筛选题目列表，`ProblemBankService.list_problems` 新增 `tag` 参数，通过 `problem_tag_map`/`problem_tags` 关联查询）。
- **前端**：新增 `ProblemTagChips.vue`，`concept`/`difficulty`/`source` 始终展示，`topic` 标签折叠在"展开/隐藏算法标签"按钮之后（对应参考图"隐藏算法标签"的交互）；点击任意标签 chip 会 emit 到 `ProblemBankPreviewView.vue`，设置 `activeTag` 并重新拉取题目列表（复用已有列表逻辑做筛选，未新建复杂页面），列表上方展示可关闭的"按标签筛选：xxx"提示条。

### 4. 洛谷风格 1-5 星难度

- **映射规则**（`clean_and_transform.py::compute_star_difficulty`）：优先使用原始 `difficulty` 字段（观察到取值范围约 0~5），直接夹取（clamp）到 `[1, 5]`（`difficulty=0` 按最低难度归为 1 星，避免出现"0 星"这种无意义值）；若 `difficulty` 缺失（`NULL`），退化使用 `level` 字段按相同方式夹取；两者都缺失则不设星级（`star_difficulty = NULL`，前端不渲染星级）。选择"夹取原始值"而非"分位数分档"的原因：原始 `difficulty` 取值本身已经是人工标注的 0~5 量表，语义上已经是"难度等级"，重新按分位数分档反而会扭曲原作者的主观难度判断；分布统计显示 1~5 星均有覆盖（未出现"全部题目挤在同一星级"的问题）。
- **实际分布**（70 题）：1★ 27 题、2★ 22 题、3★ 13 题、4★ 6 题、5★ 2 题（呈从易到难递减的合理分布，符合"入门题库以基础题为主"的预期）。
- **字段与展示**：新增 `problems.star_difficulty`（`SMALLINT`），详情接口 `to_dict()` 与列表接口 `to_summary_dict()` 均返回该字段；前端新增 `StarRating.vue`，1-5 颗 ★，点亮用金色、未点亮用灰色空心样式，同时提供 `compact` 模式（题目列表项）与完整模式（详情页标题旁，含"入门/简单/中等/较难/困难"文字标签）。

### 5. 标题右侧统计信息条（提交/通过/时间限制）

- **班级口径的关键取舍**：需求要求"按学生所在班级统计"，但旧系统导入的 26,756 条提交记录的 `legacy_user_id` 是脱敏后的旧账号 ID，**无法与当前 PLEX 账号体系（`User.id`/`Class`）建立任何真实映射**——这批学生大多也不是当前系统的注册用户。如果强行把这些历史提交"分配"给当前登录教师所管理的某个 PLEX 班级，等于凭空编造一份不存在的归属关系，属于伪造数据，因此**没有**这样做。
- **实际实现**：如实使用数据中真实存在的维度——旧系统的 `group` 表（8 个真实班级/群组，如"2024秋硕放中学""江南通扬24"），这些班级信息随 `solution.group_id` 一并导入为 `problem_submissions.legacy_group_id`/`legacy_group_name`。`GET /api/v1/problem-bank/problems/<id>/stats` 接口返回该题所有出现过的旧班级列表（`groups`），默认选中第一个班级的口径统计"提交数"（`submission_count`）与"通过数"（`accepted_count = status == 'AC'` 的计数），前端 `ProblemStatsBar.vue` 用下拉框（`n-select`）让教师切换查看不同旧班级的统计——**不同班级看到的数字确实不同**，满足"按班级切换"的交互诉求，但明确标注这是"旧系统导入班级"而非当前 PLEX 班级（下拉框旁 tooltip 说明），不冒充真实的当前班级归属。
- **时间限制**：原始数据无此字段，统一使用平台默认值 `DEFAULT_TIME_LIMIT_MS = 1000`（1.00s，定义在 `Problem` model 常量），接口同时返回 `time_limit_is_default: true` 标志；新增 `problems.time_limit_ms`（可为空的 `INT`）为未来逐题自定义预留位置，前端对默认值场景加了虚线下划线 + tooltip 提示"平台统一默认值，非题目原始设定"。

### 6. 中英文切换按钮

- **判定规则**（`clean_and_transform.py`，`HAS_ENGLISH_MIN_LENGTH` 阈值）：`has_english = bool(description_en) and len(description_en.strip()) >= 阈值`。清洗阶段已经把占位符 `'English Description'` 和"只剩空 `{[]}` 样例骨架、正文为空"的情况统一归一成 `description_en = None`/`''`，因此这里只需要一个长度阈值兜底，不需要对两种脏数据模式分别特判。
- **实际覆盖**：70 题中 **51 题 `has_english = true`**（有实质英文正文，可以放心切换），19 题为 `false`（占位符/空描述，不展示切换按钮）。
- **前端交互**：`ProblemDetailView.vue` 仅当 `detail.has_english` 为真时才渲染"中 / EN"切换按钮，点击后切换标题（`title_cn`/`title_en`）、描述正文、输入/输出格式的语言；**题目背景故事目前只生成了中文版本**（"小E"人设本身面向中文用户设计，双语背景会大幅增加 AI 调用成本且用户未明确要求），背景区块不随语言切换变化，此取舍已在组件注释中说明。

### 数据库迁移

新增/调整字段全部通过 Alembic 迁移落地，未绕过迁移体系：`backend/migrations/versions/20260730_0010_problem_bank_enhancements.py`（`problems` 表新增 `background_source`/`has_english`/`samples_source`/`star_difficulty`/`time_limit_ms` 五列，新建 `problem_tags`/`problem_tag_map` 两张表）。本地已通过 `python manage.py upgrade` 应用，并用 `load_sqlite.py` 重新写入全部数据（70 题 / 284 条标签关联 / 26,756 条提交记录，脚本按主键存在性判断插入/更新，可重复运行）。

### 新增脚本一览

| 脚本 | 作用 |
| --- | --- |
| `sandbox_exec.py` | 安全执行 Python/Java 参考答案生成真实样例 |
| `generate_backgrounds.py` | "小E"题目背景连续故事生成（AI 链 + 规则兜底），支持 `--force`/`--dry-run` |
| `generate_tags.py` | 规则驱动的标签生成（concept/topic/difficulty/source） |
| `finalize_manual_review.py` | 合并清洗、背景生成等各阶段产出的人工核对条目，去重后生成最终 `manual_review.md` |

---

## 十、后续优化建议（非本次硬性交付项）

- 44 条人工核对清单建议尽快由熟悉原始内容的老师/管理员逐条确认，尤其是 7 条"沙箱生成样例"建议二次人工验证边界情况覆盖度。
- 题目背景故事目前只有中文版本，如需支持英文背景需追加一轮双语生成（会增加 AI 调用次数/成本）。
- 标题统计条的"班级口径"目前只能选旧系统导入的历史班级，无法关联到当前 PLEX 真实班级——这是数据本身的限制（旧账号无法与当前账号建立映射），如果未来有新的、真实发生在 PLEX 内的题库提交数据，应改为按 `Class`/`User.class_id` 的真实关系统计，并保留当前"旧班级口径"作为历史数据的展示模式。
- 前端预览页尚未挂接到正式教师端侧边栏导航，需产品/设计确认最终信息架构位置。
- `gen_hint`（AI 生成的辅导提示，13,731 条）本次未建表导入，如后续需要展示历史提示，需要评估是否值得单独建表并处理与 `problem_submissions` 的外键完整性（本次清洗环节已识别出 1,137 条会因提交记录去重而产生悬空引用）。
