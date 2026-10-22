# PLEX 试用准备：账号、邮件找回与知识检索

日期：2026-10-14。正式技术栈仍为 Vue 3 / Flask / SQLAlchemy / JWT，经典与漫画主题仍独立。本次改动围绕真实用户进入系统和账号恢复，不代表已经完成商业上线验收。

## 已实现的账号流程

- 注册分别填写用户名、昵称、真实邮箱、密码与确认密码，不再生成 `@plex.local` 邮箱。用户名 3–30 位，密码 8–128 位并包含字母、数字；公开注册只能创建学生账号。
- 支持用户名或邮箱登录，忽略账号大小写。不存在、错误密码、不可用账号返回统一失败文案。
- 注册、登录、密码找回与重置采用数据库持久化的 IP / 账号固定窗口限流，跨进程共享；返回 429 和 Retry-After。限流键经过 HMAC，不明文保存账号或 IP。反向代理部署需单独配置可信代理，当前仅使用 remote_addr。
- 退出撤销当前登录会话；修改或重置密码提升用户会话版本，使所有旧 Access / Refresh Token 失效。被冻结账号不能继续刷新或使用现有令牌。
- 前端合并同一会话的并发刷新请求；新旧会话切换时避免覆盖新令牌；刷新期间网络中断不清除有效的本地登录状态。
- 密码找回使用 15 分钟一次性随机令牌，数据库仅存令牌哈希；新密码提交后，同批其他重置链接和旧登录状态全部失效。链接令牌放在 URL fragment，页面读取后清除地址栏中的凭证。
- 未配置邮件时，界面明确显示暂未开通。发送接口对不存在邮箱及发送失败使用相同文案；发送失败写入不含凭证的日志。同步 SMTP 的响应时间仍可能区分存在与不存在的邮箱，后续应改为受控邮件队列。
- Google / GitHub 入口只在服务配置完整时展示。OAuth state 绑定浏览器且 10 分钟过期，邮箱必须由供应商验证，不自动按邮箱合并已有账号。新 OAuth 账号使用不可预测的随机密码，旧版本可预测 OAuth 默认密码拒绝用于密码登录。
- 开发启动只创建缺失演示账号，不再覆盖已有密码、状态。
- 发布清单遵守 Git 忽略规则，并排除私有 `.env.*` 配置（保留示例），避免本机邮箱授权码及还原的私有资产混入后续交付清单。

## API 合约增量

统一前缀 `/api/v1`，返回 `{code, message, data}`。

| 方法与路径 | 输入 | 结果 |
|---|---|---|
| GET `/auth/capabilities` | 无 | registration_enabled、password_reset_enabled、support_email、oauth_providers |
| POST `/auth/register` | username、email、real_name、password；role 仅 student | 201，用户信息和令牌 |
| POST `/auth/login` | username（也可填写邮箱）、password | 200，用户信息和令牌；失败 401 |
| POST `/auth/forgot-password` | email | 200，统一提示；未配置邮件 503 |
| POST `/auth/reset-password` | token、password | 200；失效/已用链接 400 |
| POST `/auth/logout` | Access JWT；可选 refresh_token 用于旧客户端兼容 | 撤销当前会话，200 |
| POST `/auth/refresh` | Refresh JWT | 新 Access Token；失效/禁用用户 401 |

新增迁移 `20261014_0016`，创建 auth_session_states、auth_tokens、auth_rate_limits、oauth_identities 四张表，不修改学习记录。已在本机 MySQL 执行 upgrade。部署时先备份数据库，再执行 `python manage.py upgrade` 并检查 Alembic revision 与实际表结构，不能仅凭进程存活判断迁移成功。

## QQ 邮箱开通步骤

1. 用户本人登录 https://mail.qq.com/ ，进入设置中的账号/账号与安全区域，找到 POP3/IMAP/SMTP 服务管理，开启 SMTP。
2. 按 QQ 邮箱提示完成手机验证，生成授权码。使用的是 SMTP 授权码，不是 QQ 登录密码。页面名称以当前 QQ 邮箱为准。
3. 在项目根目录终端运行：

```powershell
.\.venv\Scripts\python.exe backend\scripts\configure_qq_smtp.py
```

脚本询问 QQ/Foxmail 地址和授权码（隐藏输入），通过 `smtp.qq.com:465` SSL 验证 SMTP 登录后，写入 Git 忽略的 `backend/.env.smtp.local`。脚本不发送邮件。不要把授权码贴到聊天、文档、GitHub 或截图。

4. 重启后端，确认 `/api/v1/auth/capabilities` 的 password_reset_enabled 为 true，再由用户用自己的邮箱触发一次找回，检查收信及链接。2026-10-14 已完成 QQ SMTP SSL 登录验证并保存本机配置；22:24（北京时间）已重启后端，后端直连和前端代理均确认密码找回能力启用。本次没有发送邮件，真实邮件投递仍未验收。

`FRONTEND_BASE_URL` 必须是收件人能够打开的站点地址；本机 localhost 链接仅适合本机测试，上线需改为公开 HTTPS 域名。该实现采用 SSL SMTP，465 为 QQ 示例；不能仅把端口改成 587 而继续使用 SMTP_SSL。

## 知识检索修复

现有 Chroma 索引记录了 sysdb 第 10 版迁移，本机原 chromadb 1.1.1 初始化报 Rust 越界异常。先复制索引到忽略目录 `output/chroma-compat/index-copy`，用 chromadb 1.5.9 验证可以打开原有 1380 个向量，再升级本机依赖；原索引未删除。

可选持久化依赖清单：`backend/requirements-knowledge.txt`。默认基础 requirements 仍允许没有 Chroma 的环境使用本地实现。升级 Chroma 前应在副本验证，不应删除 SQLite migrations 记录或把空索引当作修复成功。

升级后实际 `/knowledge/index/status` 返回：8 份文档 READY，460 个当前片段均已嵌入，没有运行中或失败任务；向量库包含历史版本，向量总数不等同于当前片段数。实际 `/rag/retrieve` 对 Python for/range 边界查询返回 3 条重排结果，向量、词法、图谱三路均有召回，knowledge_grounded 为 true。此次是链路可用性核验，不能据此宣称检索准确率或学习效果提升。

## 试用边界与后续优先级

当前可以准备受控的小范围试用。注册邮箱目前只校验格式，尚未实现注册前邮箱所有权验证；历史虚拟邮箱账号需要管理员协助补录真实邮箱。尚未实测 QQ 收信，也未完成公网部署、压力测试和外部 OAuth 供应商端到端验收。

后续优先完成：注册邮箱验证与邀请准入；新学生加入班级与首次学习目标引导；把一次诊断明确关联到推荐练习及完成结果；记录失败、首字时间、回答来源、单次模型成本与用户反馈。在同一模型与题目下分别评估检索质量、教学适配及学习前后测，避免把漂亮界面或模型接入数量当成商业价值证据。

浏览器测试插件缺少运行依赖，桌面窗口读取也返回窗口归属错误，故本轮不能把浏览器交互、移动端排版或收件箱投递标为已验收。已执行的接口测试、构建及运行核验另见验证记录。

## 验证记录

- 认证专项：`python -m pytest tests/test_auth_readiness.py tests/test_auth_oauth.py -q`，21 项通过（包括旧 OAuth 默认密码拒绝、退出撤销、过期/重复使用链接和禁用账号）。
- 前端会话行为：`npm run test:auth`，5 项通过，覆盖并发刷新、账号切换、网络失败、刷新失效和错误密码不触发刷新；已加入 CI。
- 前端：`npm run build` 通过，包括类型检查、生产文案检查、构建和包体预算。
- 后端全量：本轮首次完整运行 220 项，219 项通过，发布清单检查 1 项失败；修复清单文件选择和私有配置排除后，发布检查文件全部 6 项通过。未在修复后重跑整个 220 项套件；不能将首次全量运行写为全部通过。
- 数据库：本机 MySQL upgrade 成功；隔离 SQLite 验证本次迁移升级、重复执行、降级和再升级通过。
- `git diff --check`、仓库现有密钥扫描通过；`.env.smtp.local` 确认被 Git 忽略。
- 运行验证：前端 5180、后端 5100 返回 HTTP 200；实际检索返回 3 条课程片段。QQ SMTP 登录验证已通过；2026-10-14 22:24（北京时间）后端重启成功，后端与前端代理均返回 password_reset_enabled=true。
