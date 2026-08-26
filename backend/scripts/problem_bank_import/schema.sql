-- ============================================================================
-- PLEX Universe / A3 —— 题库更新（任务1）建表脚本
--
-- 来源：对旧版类 HydroOJ/Mulberry 题库系统的 mysqldump 导出
--       (_incoming_data/learning_core_groups_masked_normal.sql) 清洗后的
--       标准化结构，详见同目录 REPORT.md。
--
-- 字符集：全表使用 utf8mb4 / utf8mb4_unicode_ci，与仓库其余 MySQL 建议保持一致。
-- 执行方式：mysql -u <user> -p <database> < schema.sql
-- 幂等性：全部使用 CREATE TABLE IF NOT EXISTS，可重复执行。
-- ============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------------------------------------------------------
-- 表：problems —— 清洗后的标准题目表（任务1核心表，支撑任务2的题目详情展示）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `problems` (
  `id`                  INT NOT NULL COMMENT '主键，沿用旧系统 problem.id，便于审计追溯与增量重导',
  `problem_no`          VARCHAR(8)   NOT NULL COMMENT '题号，形如 A001，字母代表 concept 分组，数字为组内序号（见 REPORT.md 映射表）',
  `concept`             VARCHAR(50)      DEFAULT NULL COMMENT '原始知识点标签（Basics/Loops/Functions 等）',
  `concept_group`       CHAR(1)      NOT NULL COMMENT 'concept 归并后的题号字母分组',
  `title_en`            VARCHAR(200) NOT NULL COMMENT '英文标题（已清洗空白）',
  `title_cn`            VARCHAR(200) NOT NULL COMMENT '中文标题（已清洗空白）',
  `background`          TEXT             DEFAULT NULL COMMENT '题目背景（可选）；原始数据未与描述正文区分，暂留空由前端按需隐藏',
  `description_en`      TEXT             DEFAULT NULL COMMENT '英文描述正文，已去除 {[...]}/HTML 标记，转换为 Markdown',
  `description_cn`      TEXT             DEFAULT NULL COMMENT '中文描述正文，清洗规则同上',
  `input_format_en`     TEXT             DEFAULT NULL COMMENT '英文输入格式说明（从描述正文提炼，找不到则为空）',
  `output_format_en`    TEXT             DEFAULT NULL COMMENT '英文输出格式说明',
  `input_format_cn`     TEXT             DEFAULT NULL COMMENT '中文输入格式说明',
  `output_format_cn`    TEXT             DEFAULT NULL COMMENT '中文输出格式说明',
  `samples_json`        JSON             DEFAULT NULL COMMENT '结构化样例数组 [{"input":"..","output":".."}]，纯文本可直接复制',
  `notes_json`          JSON             DEFAULT NULL COMMENT '说明/提示字符串数组，找不到则为空数组（不杜撰）',
  `difficulty`          INT              DEFAULT NULL COMMENT '原始难度值（数值越大越难，沿用旧系统刻度）',
  `level`               INT              DEFAULT NULL COMMENT '原始关卡/等级值',
  `topic`               INT              DEFAULT NULL COMMENT '原始主题分类编号（旧系统内部编码，含义未完全枚举，保留原值供参考）',
  `reference_answer`    TEXT             DEFAULT NULL COMMENT '参考答案代码',
  `template`            TEXT             DEFAULT NULL COMMENT '学生端起始代码模板（原 template 字段，可能为空）',
  `legacy_problem_name` VARCHAR(100)     DEFAULT NULL COMMENT '旧系统内部代号，如 HelloRabbit，便于溯源',
  `legacy_author_user_id` INT            DEFAULT NULL COMMENT '旧系统出题人 user_id（不映射到当前 PLEX 用户体系）',
  `is_active`           TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '是否启用；导入时已按旧 status/remove_time 过滤，预留后续下线开关',
  `created_at`          DATETIME     NOT NULL COMMENT '创建时间（UTC，由旧 create_time 时间戳换算）',
  `updated_at`          DATETIME     NOT NULL COMMENT '更新时间（UTC，由旧 update_time 时间戳换算，缺失时取 created_at）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_problems_problem_no` (`problem_no`),
  KEY `ix_problems_concept_group` (`concept_group`),
  KEY `ix_problems_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='标准化题库题目表（清洗自旧版 Mulberry/HydroOJ 风格题库 dump）';

-- ----------------------------------------------------------------------------
-- 表：problem_legacy_quest_map —— 题目与旧 quest（关卡剧情）的映射，保留旧系统
-- 的“任务线”结构，供后续做故事化包装/分组展示时参考，非强制关联。
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `problem_legacy_quest_map` (
  `id`                     INT NOT NULL AUTO_INCREMENT,
  `problem_id`             INT NOT NULL COMMENT '关联 problems.id',
  `legacy_quest_id`        INT NOT NULL COMMENT '旧系统 quest.id',
  `legacy_quest_title_cn`  VARCHAR(100) DEFAULT NULL COMMENT '旧系统 quest 中文标题，冗余存储便于直接展示',
  `required`               TINYINT(1)   DEFAULT NULL COMMENT '旧系统标记：是否为该 quest 的必做题',
  `sort_order`             INT          DEFAULT 0 COMMENT '旧系统内的题目顺序',
  PRIMARY KEY (`id`),
  KEY `ix_quest_map_problem_id` (`problem_id`),
  CONSTRAINT `fk_quest_map_problem` FOREIGN KEY (`problem_id`) REFERENCES `problems` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='题目与旧 quest 关卡的映射（保留旧系统任务线结构，供未来参考）';

-- ----------------------------------------------------------------------------
-- 表：problem_submissions —— 清洗后的提交记录表（任务1核心表，支撑任务2的提交
-- 记录展示：AC 情况 / OI 标准评分 / 用时 / 空间 / 可复制代码）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `problem_submissions` (
  `id`                     INT NOT NULL COMMENT '主键，沿用旧系统 solution.id，便于审计追溯与 prev_solution 重试链回溯',
  `problem_id`             INT NOT NULL COMMENT '关联 problems.id',
  `legacy_user_id`         INT NOT NULL COMMENT '旧系统 user.id（不映射到当前 PLEX 用户体系，仅作展示与溯源）',
  `legacy_username`        VARCHAR(100)  DEFAULT NULL COMMENT '旧系统账号名，如 SF2437',
  `legacy_student_name`    VARCHAR(50)   DEFAULT NULL COMMENT '旧系统学生姓名（脱敏后如 学生_037）',
  `legacy_group_id`        INT           DEFAULT NULL COMMENT '旧系统班级/群组 id',
  `legacy_group_name`      VARCHAR(150)  DEFAULT NULL COMMENT '旧系统班级/群组名称，冗余存储便于直接展示',
  `code_content`           MEDIUMTEXT    NOT NULL COMMENT '学生提交的完整代码，前端只读展示+一键复制',
  `status`                 VARCHAR(8)    NOT NULL COMMENT '旧系统判题结论：AC=完全通过 / TE=编译通过但未全部通过测试 / CE=编译错误 / UE=运行时未知错误（如超时被杀、非常规异常），见 REPORT.md 推断依据',
  `is_accepted`            TINYINT(1)    NOT NULL COMMENT '是否为 AC（status = ''AC'' 的冗余布尔字段，便于查询筛选）',
  `compile_success`        TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否编译/语法检查通过',
  `test_success`           TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否全部测试点通过（等价于 is_accepted）',
  `score_points`           INT           DEFAULT NULL COMMENT 'OI 赛制得分：已通过的测试点数（原 points 字段，直接复用，见 REPORT.md）',
  `score_total`            INT           DEFAULT NULL COMMENT 'OI 赛制满分：总测试点数（原 total_points 字段）',
  `score_percent`          DECIMAL(5,1)  DEFAULT NULL COMMENT '按 OI 标准折算的百分比得分 = score_points / score_total * 100，导入时预计算避免前端重复运算',
  `test_case_results_json` JSON          DEFAULT NULL COMMENT '按测试点拆分的判题明细 [{seq,label,output,passed}]，解析自旧 output 编码（见 REPORT.md）',
  `raw_judge_output`       MEDIUMTEXT    DEFAULT NULL COMMENT '无法解析为测试点明细时（编译错误/运行崩溃）保留的原始判题输出，便于人工排查',
  `exec_time_ms`           INT           DEFAULT NULL COMMENT '判题执行耗时，单位毫秒（原 test_time 字段）',
  `exec_memory_kb`         INT           DEFAULT NULL COMMENT '判题内存占用，单位 KB（原 test_space 字段；本批次数据中恒为 0，说明旧系统未启用内存统计，见 REPORT.md）',
  `time_spent_seconds`     INT           DEFAULT NULL COMMENT '学生本次作答耗时，单位秒（原 time_spent 字段）',
  `self_confidence`        INT           DEFAULT NULL COMMENT '学生提交前的自评信心值 1-5（原 confidence 字段）',
  `legacy_error_name`      VARCHAR(100)  DEFAULT NULL COMMENT '编译/运行异常类型（如 SyntaxError），仅编译失败时有值',
  `returncode`             INT           DEFAULT NULL COMMENT '判题进程退出码：0=正常运行 / 1=编译错误 / -9=被杀（多为超时）/ -1=其他未知错误',
  `legacy_prev_solution_id` INT          DEFAULT NULL COMMENT '旧系统同题重试链：指向上一次提交的 id（非强 FK，允许指向已被清洗掉的记录）',
  `submitted_at`           DATETIME      NOT NULL COMMENT '提交时间（UTC，由旧 create_time 时间戳换算）',
  PRIMARY KEY (`id`),
  KEY `ix_submissions_problem_id` (`problem_id`),
  KEY `ix_submissions_legacy_user_id` (`legacy_user_id`),
  KEY `ix_submissions_status` (`status`),
  KEY `ix_submissions_problem_user` (`problem_id`, `legacy_user_id`),
  CONSTRAINT `fk_submissions_problem` FOREIGN KEY (`problem_id`) REFERENCES `problems` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='标准化题目提交记录表（清洗自旧版 Mulberry/HydroOJ 风格题库 dump 的 solution 表）';

SET FOREIGN_KEY_CHECKS = 1;
