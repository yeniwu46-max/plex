# 小 E 学习文档与知识图的统一辅导链路

## 使用与行为

在学生端“驿站助手”输入编程学习主题，通过加号菜单选择“生成文档”或“生成知识图”。两个工具复用 TutorService，按照授权课程检索、结构生成、教学审核、来源复核的顺序执行。文档输出章节；知识图输出节点和关系，由服务器生成 Mermaid，模型不能提交脚本、点击命令或任意图表语法。

新工具使用任务开始时固定的学习画像与 LearnerState，记录来源模式及版本。画像只提供已有白名单维度，年龄不作为新增模型输入。生成文档或下载本身不表示学生看懂了内容，不写入提示展示回执、掌握度或学习行为证据。普通聊天的四种帮助入口保持原来的职责。

有课程依据且结构、引用、教学审核均通过才返回成功；证据不足、模型异常、伪造引用、审核不通过均明确显示“学习材料暂未生成”。不使用本地示例模板伪装生成成功。考试禁用或仅概念辅导的限制同样生效，调用方不能自带课程来源或放宽策略。

## 记录、撤回与下载

复用私有 TutorSession/TutorTurn，无新增数据库表或迁移；现有主库版本为 20261017_0028。新增 learning_document / knowledge_graph 两种内部动作，策略版本为 tutor-modes-3，普通 `/tutor/ask` 不开放这两个模式。

相同 request_id 和原始请求返回既有结果，不重复调用模型；同一编号更换参数返回 409。既有请求租约处理并发与失败恢复。恢复和下载通过本人接口取回，跨账号返回 404。发布前及后续读取检查账号、题目权限、全部输入课程依赖的权限、版本与正文哈希；材料撤回、换版或原版本正文被改写均拒绝返回旧正文。旧记录没有哈希时保留原有版本校验，不伪造历史摘要。

前端的新产物缓存仅保留私有请求编号和类型。恢复或页面重新可见时清除旧显示并重新核对；下载前再次读取服务器，不直接下载浏览器缓存。会话或账号切换取消浏览器等待并丢弃晚到结果；同一页面的重试保持原主题与请求编号。并发恢复有递增检查编号，较旧响应不能覆盖较新的拒绝结果。移除假流式逐字展示与虚构的阶段耗时。

没有服务器编号的旧版产物仍按原有方式保留，不批量清空用户聊天。已经显示、复制或下载到用户设备的内容无法远程撤回。浏览器取消等待也不等于服务端模型请求已取消；端到端取消仍属后续 P4。

## 接口

学生 JWT 与本人权限必需，统一 `{code,message,data}`。

- `POST /api/v1/student/messenger/tools/learning-document`
- `POST /api/v1/student/messenger/tools/knowledge-graph`
- `GET /api/v1/student/messenger/tools/artifacts/<request_id>`

POST 推荐 `{topic, request_id}`，主题 2–500 字。兼容旧 `message` 别名；两者同时存在必须相同。可选可信题目上下文 `session_id/question_ref/formal_question_id/question_version/code/run_id`；额外字段拒绝，题目与执行记录仍由服务器验证。旧客户端缺少编号时由服务器生成，重试去重需要客户端保留原编号。

返回增加 `artifact_id/request_id/session_id/kind/status/title/markdown/mermaid/knowledge/evidence_status/evidence_notice/policy_result/learning_context`。保留旧 topic/backend 字段；illustration 为空，不创建无鉴权的公开插图。来源 DTO 不包含全文哈希、检索分数或原始学习档案；版本和受保护的来源入口保留。`knowledge.latency_ms` 是实际本次检索、生成与审核耗时，不是首字时间或并发性能指标。

## 验证记录

- SQLite 辅导、上下文、兼容及工具回归：118 项通过，output/plex-p2-artifacts-sqlite.log。
- 最后补充 JSON 运算符保留与普通文本转义后的 SQLite 工具/知识层/反例生成回归 51 项通过（output/plex-p2-artifacts-final-sqlite.log）；与上面的 118 项有交集，不合计为独立测试数量。
- 临时独立 MySQL 库专项 18 项通过、310 项未选中（output/plex-p2-artifacts-mysql.log），测试库清理完成。
- 前端实际组件异步行为测试：16 项通过，output/plex-p2-artifacts-frontend.log，覆盖同请求重试、账号/会话切换、恢复竞态、下载拒绝、缓存与账号隔离。
- 前端类型检查、生产文案、构建及包预算通过：output/plex-p2-artifacts-build.log。
- 最终真实 HTTP 与模型记录：output/plex-p2-artifacts-live-preserved.json。临时独立 SQLite、合成课程资料、真实本地索引/BM25/图谱检索；DeepSeek deepseek-chat 分别完成文档与知识图生成及审核，共 4 次调用。文档观测 4872ms、知识图 3587ms，各有 1 条课程来源。相同请求重试和恢复一致、不增加模型调用；撤回后两个 GET 均返回 409。
- 最初知识图的伪造引用被拒绝，记录保留在 output/plex-p2-artifacts-live.json；补充逐字复制 chunk_id、区分文档/图节点 ID 的生成约束。中途格式保留参数的实现错误曾导致模型不可用，已修复并重测，不将失败记录算作成功。
- 结构化 JSON 保留乘号与幂运算符，不沿用普通聊天的星号格式清理。服务端对普通文本做 Markdown 转义，包括防止裸域名被前端自动转成链接；只有服务端排版与来源控件创建结构。

以上是工程与单次真实链路验证，不是模型正确率、课堂效果、并发指标、Chroma 或 Docker 验收。浏览器实际视觉、四种主题组合、多尺寸及键盘验收继续受既有 URL 安全限制，未绕过。

## 本地服务

确认资源任务、候选任务及有效租约辅导任务均为零后重启后端，父进程 47352，监听进程 45472；前端 38476 保持运行。前端 5180/后端 5100 均可访问；健康与页面 HTTP 200，工具未登录 401，本人不存在记录 404。主库仍为 20261017_0028，无迁移、重置、补种或验收数据写入。只读记录：output/plex-p2-artifacts-http.json。

## 后续

P2 真实执行轨迹、P0 教师标注基线、P4 端到端取消、用量、配额与真实试用仍未完成。Docker 当前不可用；最终反例目录仅 10/30 完成真实执行复验，其余 20 道与全部真实教师审核仍待完成。没有本轮 Git 提交或推送。
