# Python 逐行执行轨迹

> 2026-10-19 状态更新：独立合成环境已完成真实 Docker 浏览器走查及四外观/四尺寸，并修复手机布局与浅色对比，见[最新页面验收](2026-10-19-python-trace-page-acceptance.md)。下文“等待浏览器走查”保留为原阶段记录；主环境轨迹开关仍关闭。

本阶段落实四模块方案中 KITE 对照的“执行证据与教学动作分开”部分。它记录学生短程序的一次实际自测，供学生和小 E 对照；不据此宣称算法普遍正确、题目通过或学生已经掌握。

## 实现与边界

- 新增 `POST /api/v1/code/trace`，只接受本人有效学生 JWT。输入为 `code`、可选 `stdin`、`language` 和既有题目引用/版本字段。拒绝浏览器传入的运行报告、通过标记、其他账号等额外字段。
- 使用现有 Docker 执行适配器，沿用无网络、非 root、只读根文件系统、资源限制、短生命周期容器等设置。不在 Flask 进程或宿主机执行学生代码；Judge0 暂不开放这一轨迹契约。
- Python 子集允许赋值、条件、循环、基础集合及明确列出的内置函数。拒绝导入、属性访问、用户函数/类、推导式、动态调用、双下划线名称和覆盖内置函数。AST 限制用于防止修改或访问轨迹器，不能替代容器隔离。
- 代码最多 12 KiB、200 行、1,000 AST 节点；标准输入最多 4 KiB。每次最多记录 80 个行事件，每条快照至多 6 个变量，限制嵌套层级、预览长度与整体大小，循环引用显示为预览标记。输出最多 4 KiB。
- `sys.settrace` 在容器内记录**该行执行前**的变量快照；另给出停止时的变量。遇到运行时异常、80 步上限或输出上限时保留已经完成的有限记录；容器被终止而无法得到完整报告时不编造轨迹。
- 服务端核对随机 nonce、规范化代码 SHA-256、固定协议字段、行号、类型和大小。返回实际容器镜像 SHA、Python 版本、原始/规范化代码哈希以及输入哈希。nonce 不对外返回、不入库。
- 记录保存在既有 `TutorCodeRun`，`execution_kind=trace`、`evidence_scope=self_test`；无需迁移。引用必须属于本人且匹配代码、题目及题目版本，执行前后复核权限。不创建正式成绩、学习事件或掌握度更新。

## 与小 E、前端的连接

试炼代码区增加独立“查看逐行轨迹”面板和可选标准输入。开启开关后才展示；不会自动执行、不附带题目的隐藏测试或自动判题。账号、题目、代码、输入变化或页面卸载使未返回的结果失效。

小 E 接收已有本人运行记录。向模型发送的轨迹最多保留前 8 条和后 2 条，明确总数及省略数；数据库保留完整的有限记录。`algorithm_trace` 回答的 `execution_trace` 由服务端填入，模型不能生成该字段。模型推演说明与执行快照分别展示，即使运行记录存在，也不将模型全部讲解标为已验证。没有真实记录时继续标注为说明性推演。

面板使用当前主题的颜色，漫画样式仅在 `data-plex-style=comic` 下改变边框。代码和值使用 Vue 文本插值，支持换行、键盘焦点及滚动区域，没有持续动画。

## 接口补充

`GET /api/v1/code/languages` 的 `data.execution.trace` 返回 `enabled`、`backend_supported`、`policy`、上限、支持范围和 `execution_health_verified=false`。这是配置声明，不探测或保证引擎在线。

`POST /api/v1/code/trace` 成功返回已有 `run_id/code_hash/question_version`，以及 `trace_status=recorded|sandbox_limit`、`trace`、`graded=false`、`evidence_scope=self_test`。`trace` 包括 `steps[{line,variables:{values,omitted}}]`、`final_variables`、`outcome`、`completed`、`last_line`、标准输入输出、错误类型/消息和运行来源信息。

未授权 401、非学生 403、输入不合法 400、题目/权限变更 409、关闭开关或隔离执行故障 503。503 不创建运行记录；重试不视为一次正式作答。语法/子集校验失败要求调整代码或改用普通运行。

## 启用条件与当前状态

`CODE_TRACE_ENABLED=false` 为默认值。2026-10-18 Docker 恢复后，**10 项真实容器执行验收全部通过；运行开关仍保持关闭，等待浏览器走查**。这仅验证所列 Python 子集案例，不代表任意程序或全部界面已验收。

在引擎及现有隔离镜像可用的环境中，从 `backend/` 执行：

```powershell
../.venv/Scripts/python.exe scripts/check_python_trace_sandbox.py --output ../output/python-trace-acceptance-new.json
```

脚本只使用 10 个人工编写的合成小程序，在 Docker 内检查赋值前快照、循环边界、空集合、标准输入、字典、全角规范化、循环引用、报错、步数限制和输出限制。它不访问业务数据库，不启动/重置 Docker，不执行宿主机回退，不改变运行服务的开关，也不覆盖已有验收文件。只有报告 `verified=true`、10 项实际通过，且浏览器走查通过，才应为受控试用开启本机配置；关闭开关可以停止新轨迹请求，历史本人记录仍可查看。

契约测试中的执行器为 mock，不能当作真实运行验收。SQLite/MySQL 检查记录持久化、归属、代码/题目版本、不产生学习副作用；前端脚本检查异步结果不会进入其他账号/题目。四主题、多尺寸、键盘及真实轨迹的浏览器走查仍待完成。

首次失败输出 `output/plex-python-trace-sandbox-20261018.json` 保留为历史。恢复后的新报告为 `output/plex-python-trace-sandbox-20261018-recovered.json`：`verified=true`，10 个案例全部通过；检查了行前快照、循环边界、空集合、标准输入、字典、全角规范化、循环引用、运行异常、80 步上限和输出上限。报告记录 Docker 镜像 SHA 与 Python 3.12.15；三份执行实现文件的摘要已与当前源码复核一致。总核对记录为 `output/plex-docker-recovery-acceptance-20261018.json`。未在主库创建记录，也未自动打开运行服务开关。
