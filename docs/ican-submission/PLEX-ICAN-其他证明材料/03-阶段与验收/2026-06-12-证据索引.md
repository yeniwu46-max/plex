# PLEX A3 证据索引

**更新时间：2026-06-12**

本索引只链接可重复执行、可追溯到代码或数据库记录的证据。Mock、本地规则和外部真实服务验收严格分开。

## 状态口径

| 状态 | 含义 |
|---|---|
| 已真实验收 | 已在对应真实环境或真实外部服务运行并留存证据 |
| 本地规则验收 | 使用本地 SQLite、规则后端或确定性测试通过，不等同真实大模型 |
| 外部条件阻塞 | 代码和脚本已准备，但缺凭证、联网、Docker 或 GitHub 登录 |
| 尚未实现 | 不进入答辩“已完成功能”口径 |

## 核心证据

| 能力 | 状态 | 证据 |
|---|---|---|
| 双画像个性化与五类资源 | 本地规则验收 | `backend/reports/a3-personalization-local/` |
| 三轮反馈闭环 | 本地规则验收 | `backend/reports/a3-personalization-local/feedback-loop-three-rounds.json` |
| 学习效果前后测 | 本地规则验收 | `backend/reports/a3-next-stage/learning-effect.json` |
| 安全专项 | 本地规则验收 | `backend/reports/a3-next-stage/security-validation.json` |
| 并发、幂等与恢复 | 本地规则验收 | `backend/reports/a3-next-stage/performance-recovery.json` |
| 干净环境检查 | 本地环境验收 | `backend/reports/a3-next-stage/clean-environment.json` |
| Python 3.12 / Node 20 / MySQL 8 CI | 外部条件阻塞 | `.github/workflows/ci.yml` 已配置；待 GitHub Actions 运行链接 |
| 真实讯飞画像、资源、驿站冒烟 | 外部条件阻塞 | `backend/scripts/smoke_iflytek.py`；缺 `IFLYTEK_SPARK_API_PASSWORD` |
| 讯飞 TTS | 尚未实现 | 不作为当前功能宣传 |

## 2026-06-12 本地结果

- 学习效果：前测 3 次错误，后测 3 次正确，正确率与掌握度变化 `+100`，错题变化 `-3`；证据 ID 可追溯。
- 安全专项：提示注入、超课程范围、敏感内容、知识库越权、教师审核越权、非法资源类型、扩展名伪装和阻断后不持久化全部通过。
- 性能恢复：8 个并发请求成功率 `100%`，P50 `106.86ms`，P95 `162.03ms`，幂等率 `100%`，仅形成 1 个任务和 5 个资源；过期 `running` 任务转为可恢复失败，已完成任务保持完成。

上述性能数据来自本机隔离 SQLite 和 `local_rules` 后端，只用于本地工程基线，不冒充生产 MySQL 或真实讯飞性能。

## 统一验证

```bash
cd backend
python manage.py upgrade
python manage.py seed-demo
python manage.py knowledge-check
python scripts/verify_learning_effect.py
python scripts/verify_security.py
python scripts/verify_performance_recovery.py
python scripts/verify_clean_environment.py
python scripts/scan_secrets.py
python -m pytest -q
```

```bash
cd frontend
npm ci
npm run build
```
