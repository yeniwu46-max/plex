# HTTP 页面 AI 请求兼容修复

## 原因与修改

公网 `http://pltek.cn` 不具备浏览器安全上下文。资源生成调用
`crypto.subtle.digest` 时抛异常；小E发送和编程辅导调用
`crypto.randomUUID` 时抛异常，导致请求无法发出。
本地 localhost 可以使用这些 API，因此此前本地检查没有暴露问题。

- 新增 `frontend/src/utils/browserCrypto.ts`：优先使用原生 API；
  HTTP 使用 `getRandomValues` 生成 UUID v4，使用 `@noble/hashes` 计算 SHA-256。
- 资源和 RAG 的摘要算法、缓存键格式、账号隔离及重试请求 ID 复用保持一致。
- 小E对话、辅导浮窗、运行反馈、学习证据和反例练习使用共同的请求 ID 方法。
- 新增真实 HTTP 能力缺失的测试环境，覆盖中文摘要、UUID、资源重试、
  RAG 重试及小E按钮到请求/回复的完整前端流程。

## 验证与发布

2026-10-21（北京时间）：

- 前端全部 145 项测试通过，生产构建及文案/包体积检查通过。
- 公网 Chrome 修复前复现 `crypto.randomUUID is not a function`。
- 修复后公网 HTTP 小E成功回答 Python for 循环问题。
- 公网 HTTP 完整学习包任务达到 100%，生成内容可打开。
- 自主练习的小E浮窗成功返回“只提示下一步”辅导回答。
- 公网 IP 的 HTTPS 健康接口正常通过证书验证并返回 200。

发布目录：`/opt/plex-a3/releases/20261021-http-crypto`。
前端备份：`/opt/plex-a3/frontend-dist.rollback-20261021-http-crypto`。
静态资源先发布，首页原子替换；保留旧资源文件供已打开页面使用。

## 已知状态

“未绑定服务器题面”表示当前练习没有关联可验证的正式题面，
按自主代码讨论处理，不影响提问。课程检索仍提示证据不足时，
小E会标明通用帮助，资源使用内置课程材料；生成内容仍保留审核提示。
