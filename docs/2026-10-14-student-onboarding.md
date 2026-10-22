# PLEX 首次入驻与账号外观

## 用户流程

新学生账号通过注册、第三方首次注册或管理端代建后，进入独立页面 `/student/onboarding`。流程为「了解你 → 选择外观 → 入驻仪式」。已有学生不自动进入，可在「账号设置 → 个人资料 → 入驻资料」或学习画像页主动编辑。

问卷包含年龄范围、编程基础、从事领域；其他领域说明最多 50 字。前三项必须选择才能提交，也提供不透露/不确定选项。点击「稍后填写」清空草稿、不保存未提交的资料，保留选择的外观。

草稿经过 500ms 防抖保存到服务器，当前标签页另存恢复缓存；网络失败保留草稿并展示重试。完成状态和欢迎确认分开保存：仪式中途关闭后重新进入会恢复欢迎展示，点击「开启探索」才确认。原目标必须是存在的学生路由，默认学生首页。入驻页面不挂载学生布局和新手导航。

仪式约 6 秒，分启航、抵达和徽章三个阶段。随时可跳过动画；减少动态效果偏好下直接展示静态欢迎卡。没有视频和自动声音。

## 状态与编号

`student_onboarding` 每个学生最多一条：

| 字段 | 含义 |
| --- | --- |
| `status` | `pending` 待入驻、`completed` 已提交、`skipped` 已跳过、`exempt` 已有账号免引导 |
| `answers` / `draft` | 已提交答案 / 未完成草稿；年龄仅存这里 |
| `survey_version` / `step` | 问卷版本 1 / 草稿步骤 1 或 2 |
| `adventurer_number` | 唯一且永久固定的入驻编号，已有账号补填不分配 |
| `completed_at` / `welcomed_at` | 入驻完成 / 点击开启探索时间 |

`adventurer_counter` 单行基数为 200，首个成功完成或跳过的账号获得 201。历史基数只是展示编号的起点，不代表实际用户数，也不创建占位用户。账号停用不回收编号。

完成事务按账号加锁、检查状态、保存外观、条件更新待入驻状态、原子递增计数、保存答案与画像历史，最后统一提交。唯一约束防止重复编号；重试返回既有结果；失败全部回滚。MySQL 使用当前读和外观 upsert，避免并发首次保存产生空区间锁冲突；SQLite 通过写事务串行化。迟到的 `draft_only` 草稿不会覆盖已完成或跳过的答案。

## 画像与隐私边界

- 编程基础映射到 `knowledge_foundation`，领域映射到 `major_background`，带 `origin: onboarding`、`source: confirmed` 和「用户自述，未经能力测评」证据。
- 画像历史理由为 `onboarding_survey`。画像服务增加 `commit=False` 支持，由入驻事务统一提交。
- 不确定/不透露不生成虚假的能力描述；将原问卷答案改为未知会清除该问卷来源的旧值，不删除其他来源的证据。
- 年龄不写入学习画像，不进入外部模型提示；本流程不调用外部模型。问卷不改变知识掌握度、解锁条件、练习记录和成绩。

## API 契约

所有响应采用现有 `{code,message,data}` 包装，JWT 校验和账号停用校验沿用现有机制。入驻接口仅学生本人可用，不接受外部 `user_id`。

| 方法与路径 | 请求与结果 |
| --- | --- |
| `GET /api/v1/student/onboarding` | 本人 `onboarding` 摘要、`preferences`、`answers`、`draft`、`step`、`survey_version`、选项字典 `options` |
| `PATCH /api/v1/student/onboarding` | `{answers, step?, preferences?, draft_only?}`；待入驻保存草稿，其他状态编辑答案；自动保存必须传 `draft_only:true` |
| `POST /api/v1/student/onboarding/complete` | `{action:"submit"或"skip", answers, preferences}`；成功返回完整入驻状态；重复完成返回原结果 |
| `POST /api/v1/student/onboarding/acknowledge` | `{}`；幂等设置欢迎已读，返回完整状态 |
| `GET/PATCH /api/v1/users/me/preferences` | 本人外观 `{visual_style:"space"或"comic",color_mode:"dark"或"light"或"auto"}`；所有登录角色可用 |

登录、注册、OAuth 会话和 `/api/v1/users/me` 增加 `onboarding` 与 `preferences`。摘要格式：`{status,adventurer_number,welcome_pending,required}`。`required` 等于仍待入驻或仍待确认欢迎；加载失败不能视为已完成。

答案枚举：

- `age_range`: `under13 / 13_15 / 16_18 / 19_24 / 25_34 / 35plus / private`
- `programming_level`: `none / syntax / exercises / projects / professional / unknown`
- `field`: `student / software / engineering / education / creative / business / other / private`
- `field_detail`: 可选字符串，仅 `field=other` 时保存。

主题与明暗独立：经典为 `space`，漫画为 `comic`。问卷仅展示黑夜/白昼，其余设置保留 `auto`。服务器存账号偏好，本地 `plex-appearance:<id>` 缓存和匿名浏览器偏好分开；登录切换恢复对应账号，登出恢复匿名偏好。已有账号没有服务器偏好时保留原浏览器设置。同步失败有可重试提示。

## 迁移与验证

迁移 `20261014_0017` 位于 `backend/migrations/versions/`，父版本 `20261014_0016`。新增三个表，已有学生回填 `exempt`；已存在入驻记录和计数不会被重置。兼容已通过 `create_all` 创建表的本地环境。部署时先执行 Alembic upgrade，再重启后端；不要清库或重新初始化演示数据。

测试命令（仓库根目录的 `.venv`）：

```powershell
cd backend
../.venv/Scripts/python.exe -m pytest tests/test_onboarding.py tests/test_auth_readiness.py tests/test_auth_oauth.py tests/test_student_profile.py tests/test_teacher_student_trials.py -q
../.venv/Scripts/python.exe scripts/test_onboarding_mysql.py
cd ../frontend
npm run test:auth
npm run build
```

MySQL 验证脚本从本机开发配置获取连接，在独立随机命名的 `plex_onboarding_test_*` 库运行，并清理该临时库；需要创建和删除数据库权限，不打印连接密钥、不修改业务库。测试包括迁移建表/历史回填、并发跨账号及同账号请求、失败回滚、跳过后补填、画像历史、年龄隔离、权限和外观持久化。前端测试执行真实 Vue/Pinia store 与路由守卫，模拟网络失败、会话切换、偏好恢复。

验收边界：浏览器自动化运行组件缺失，无法执行实际点击、截图和 1440/1024/768/390px 的视觉检查。CSS 已提供响应式布局、焦点及减少动态效果适配，但这些浏览器体验仍需人工走查；构建和接口自动测试不能替代视觉验收。

### 本机验证结果

- SQLite 与相关后端回归：37 项通过。
- 独立 MySQL 临时库：10 项通过，包含新表迁移、历史回填与并发编号。
- 前端会话与外观测试：10 项通过；生产文案、类型检查、Vite 构建和包预算通过。
- 本地业务库已升级到 `20261014_0017`，318 个已有学生免自动引导，计数仍为 200；未用真实业务账号消费 201 号。
- 重启后通过 5180 前端代理验证登录、本人入驻状态、`/users/me` 和页面路由，均正常；SMTP 找回能力仍启用。测试会话已退出。
- 浏览器真实交互与视觉验收未完成，原因见上节。
