# PLEX 2026-06-09 开发沉淀总结

## 今日目标

将 PLEX 从可运行原型推进为可恢复、可降级、可持续验证的工程稳定候选版本，为后续真实讯飞联调和完整演示闭环打基础。

## 今日完成

### 1. 讯飞与服务状态

- 加固 Spark Lite 适配器，覆盖鉴权、限流、超时、网络异常、空响应和非法 JSON。
- 日志仅记录请求 ID、模型、耗时和脱敏错误，不记录密钥及用户隐私内容。
- 新增 AI 状态与应用健康接口：
  - `GET /api/v1/system/ai-health`
  - `GET /api/v1/health`
- 增加独立讯飞联网冒烟脚本；无凭证时明确返回 `not_configured`。
- 固化三种 AI 运行状态：`iflytek_spark`、`local_rules`、`unavailable`。

### 2. 资源生成可靠性

- 任务支持请求指纹、幂等键、画像版本和可恢复状态。
- 通过数据库条件更新实现原子领取，避免多个执行器重复处理任务。
- 应用启动时恢复待执行任务，并处理超时运行任务。
- 增加任务历史、失败重试和前端长时间处理中提示。
- 五类资源分别进行结构校验，单项异常不会抹除其他有效结果。

### 3. 内容安全与教师审核

- 为五类个性化资源增加独立 JSON Schema。
- 增加课程范围、知识库引用、置信度、敏感内容、重复题目和 Python 代码语法检查。
- 统一风险原因：
  - `low_confidence`
  - `invalid_citation`
  - `schema_invalid`
  - `safety_blocked`
  - `out_of_scope`
- 风险资源进入待审核状态，教师批准时必须填写审核说明。
- 驳回或未审核资源不会进入学生推荐。

### 4. 学习闭环

- 学生产生错题后，系统创建持久化画像更新建议。
- 学生可接受或拒绝建议；接受后生成新的画像历史版本。
- 画像变化后可重新计算路径和推荐，不自动重复生成全部资源。
- 星轨展示推荐资源及“为什么推荐给我”。
- 资源中心补齐《Python 程序设计基础》全部 16 个知识点入口。

### 5. 工程化

- 新增非破坏式管理命令：初始化、升级、迁移冒烟和幂等演示数据写入。
- Windows 与 Linux 启动脚本不再自动清空数据库。
- 固定 Python 3.12、Node.js 20 基线。
- CI 增加后端测试、前端构建、密钥扫描、SQLite 和 MySQL 8 迁移验证。
- 增加脱敏环境变量示例和本地密钥扫描脚本。

## 验证结果

| 检查项 | 结果 |
|---|---|
| 后端全量测试 | 62 项通过 |
| 前端生产构建 | 通过 |
| SQLite 空库初始化 | 通过 |
| SQLite 已有库升级 | 通过 |
| 迁移回滚与重新升级 | 通过 |
| 密钥扫描 | 通过 |
| 健康接口 | 通过，不返回密钥 |
| 讯飞真实联网 | 待配置 HTTP API Password |
| 本地 MySQL | 本机无 Docker/MySQL，交由 CI 验证 |

## 版本基线

- 核心基线提交：`cf8505f`
- 稳定性提交：`70ec2dc`
- 稳定候选标签：`plex-stability-candidate-20260609`
- 当前开发分支：`codex/pre-sprint-baseline-20260608`

## 遗留风险

1. `backend/.env` 尚未配置真实 `IFLYTEK_SPARK_API_PASSWORD`，因此真实 Spark 调用没有完成最终验收。
2. 当前开发机无法执行真实 MySQL 冒烟，需要观察 GitHub Actions MySQL 任务结果。
3. 三角色完整演示链路还需在稳定运行环境中连续执行两次。
4. 语音额度为 0，继续使用明确标记的降级内容，不能描述为实时语音生成。

## 下一次开发入口

1. 配置真实讯飞凭证并运行 `python scripts/smoke_iflytek.py`。
2. 检查 GitHub Actions，修复可能出现的 MySQL 迁移兼容问题。
3. 使用两组固定画像执行端到端差异测试。
4. 连续彩排学生错题、画像建议、路径推荐、资源生成和教师审核流程。
5. 通过稳定门槛后进入演示体验、PPT 和视频材料阶段。

## 常用命令

```bash
cd backend
python manage.py init
python manage.py upgrade
python manage.py migration-smoke
python manage.py seed-demo
python scripts/scan_secrets.py
python scripts/smoke_iflytek.py
pytest
```

```bash
cd frontend
npm run build
```
