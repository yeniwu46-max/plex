# 系统测试说明

测试分为单元与接口回归、确定性场景验证、前端生产构建、安全专项、性能恢复和干净环境检查。

截至 2026-06-12，本地结果如下：

- 后端全量：`83 passed`。
- 前端：`npm run build` 通过。
- 前端预算：首屏 109.27 KiB gzip，最大懒加载 390.50 KiB gzip，均低于 CI 阈值。
- 知识库：16/16 知识点通过结构校验。
- 安全专项：8/8 场景通过。
- 并发任务：成功率 100%，幂等率 100%，P95 173.79 ms。
- 工程检查：密钥扫描、`start.bat --check`、`git diff --check` 通过。
- 后端测试输出：零告警；项目弃用调用：0。

安全专项覆盖提示注入、课程范围外请求、敏感内容、知识库管理越权、教师审核越权、非法资源类型、扩展名伪装和阻断内容不持久化。性能报告使用固定画像并发提交，检查成功率、P50/P95、幂等率、重复资源、降级比例和重启恢复状态。

证据目录：

- `backend/reports/a3-personalization-local/`
- `backend/reports/a3-next-stage/`
- `backend/reports/a3-submission/`

项目自身弃用调用通过 `verify_deprecation_budget.py` 执行零容忍闸门：`Query.get()` 和 `datetime.utcnow()` 均必须为 0。主键读取已统一为 `Session.get()`，UTC 时间已统一使用项目兼容工具。Werkzeug 2.3 路由编译器的 AST 弃用噪声已与项目代码告警分离。

当前结果属于本地 SQLite 和本地规则后端证据。真实讯飞、GitHub 在线 CI、MySQL 8 与 TTS 不计入已通过项。
