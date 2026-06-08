# PLEX 工程稳定阶段说明

**日期**：2026-06-09
**候选目标**：可恢复、可部署、可降级、可连续演示

## 已实现

- Spark Lite 适配器增加鉴权失败、限流、上游错误、超时、网络错误、空响应和非法 JSON 分类。
- 日志仅记录请求 ID、模型、耗时和错误码，不记录密钥与用户提示词。
- 新增 `/api/v1/system/ai-health` 和 `/api/v1/health`，返回脱敏服务状态。
- 资源任务增加画像版本、请求指纹、幂等键、可恢复状态、任务历史和原子领取。
- 服务启动恢复待执行任务，并将超时运行任务标记为可重试失败。
- 五类资源使用独立 JSON Schema，联合检查置信度、课程引用、范围、安全、重复题和 Python 语法。
- 风险资源进入 `pending_review`，教师批准必须填写审核说明。
- 错题写入后创建持久化画像建议；学生接受或拒绝后才更新画像版本。
- 资源中心补齐 16 个知识点，并增加任务历史、超时提示和失败重试。
- 星轨展示个性化资源及“为什么推荐给我”。
- 原启动脚本不再自动清空数据库，统一使用 `manage.py`。

## 管理命令

```bash
cd backend
python manage.py init
python manage.py upgrade
python manage.py migration-smoke
python manage.py seed-demo
python scripts/scan_secrets.py
python scripts/smoke_iflytek.py
```

`smoke_iflytek.py` 是显式联网测试，不进入 CI。未配置凭证时返回 `not_configured`，不会尝试外网请求。

## 环境与降级

- Python 基线：3.12
- Node.js 基线：20
- 任务执行器：进程内、最多两个工作线程
- 讯飞不可用：自动使用 `local_rules`
- 语音服务量为 0：继续使用明确标记的文本/演示音频降级

真实 Spark HTTP API Password 仅写入 `backend/.env`：

```env
IFLYTEK_SPARK_API_PASSWORD=
```

## 当前外部验证状态

- SQLite 初始化及迁移回退/升级：已通过。
- MySQL：已加入 GitHub Actions MySQL 8.0 服务验证；当前本机没有 Docker/MySQL，无法本地执行。
- Spark 联网：本机 `.env` 尚无 HTTP API Password，因此当前仅完成模拟成功、限流和本地降级测试。

## 发布门槛

- 后端全量测试通过。
- 前端生产构建通过。
- SQLite 和 CI MySQL 迁移验证通过。
- 密钥扫描通过。
- 配置真实讯飞凭证后，联网冒烟返回 `ok: true`。
- 学生错题、画像建议确认、路径推荐和教师审核链路连续通过两次。

## 本地验证结果（2026-06-09）

- 后端：`pytest` 全量 62 项通过。
- 前端：`npm run build` 生产构建通过。
- SQLite：空库初始化、已有库升级、迁移回滚与重新升级通过。
- 安全：仓库密钥扫描通过，健康接口不返回凭证。
- 外部限制：本机未配置 Spark HTTP API Password，且没有 Docker/MySQL，因此真实 Spark 与本地 MySQL 验证仍需在具备对应环境后完成。
