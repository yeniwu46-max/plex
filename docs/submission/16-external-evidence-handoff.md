# 科大讯飞 990 外部证据交接包

目标 DDL：2026-10-01。此文件只记录外部协作所需的最小输入和可复核命令，不保存密钥、学生身份信息或完整敏感提示词。

## A. 讯飞 Spark / 星辰接口

### 需要企业或指导老师提供

- Spark Pro（或命题方指定版本）的测试凭证与额度；凭证只通过本机环境变量注入。
- ASR、情感 TTS、数字人接口权限及测试域名。
- 测试口径：模型名、区域、网络环境、首 Token 计时起点/终点、并发和限流规则。

### 本机配置（示例，不填入仓库）

```text
IFLYTEK_SPARK_API_PASSWORD=***
IFLYTEK_SPARK_MODEL=generalv3
IFLYTEK_TTS_APP_ID=***
IFLYTEK_TTS_API_KEY=***
IFLYTEK_TTS_API_SECRET=***
```

### 运行与验收

```text
cd D:\zhongruan\zhongruan\backend
python scripts/evaluate_iflytek_live.py --cases 100
python scripts/evaluate_voice_pipeline.py --run-rounds
```

报告必须保留：UTC 时间、模型、请求 ID、成功/失败数、解析通过数、引用约束通过数、P50/P95、错误码和实际后端。若凭证缺失，报告必须保持 `not_configured`。

## B. 真实教学实验

### 需要学校/教师提供

- 至少 1 门真实课程、负责人、班级和实验时间窗口。
- 累计不少于 100 人次真实使用记录；学生仅使用脱敏 `participant_id`。
- 前测/后测题目版本、对照方案、知情说明和数据使用授权。
- 教师工单、满意度、推荐接受率、学习时长和教师工作量记录。

### 运行与验收

```text
cd D:\zhongruan\zhongruan\backend
python scripts/analyze_iflytek990_experiment.py \
  --input data/experiments/iflytek990_events.csv \
  --output reports/iflytek-990-experiment-final.json
```

只有 `participant_count >= 100`、数据校验通过、前后测配对规则和缺失/退出处理均有记录，才能把实验状态改为 `ready`。当前模板仍为空，不能生成效果结论。

## C. MySQL 8 与最终冻结

- 使用全新 MySQL 8 数据库跑迁移、种子、登录、资源生成、反馈和教师审核。
- 生成 `backend/reports/a3-next-stage/mysql-clean-environment.json`。
- 再运行发布审计，确认 `submission_ready=true`、工作树干净、清单提交 SHA 一致。

## D. 交付物关闭顺序

1. 真实讯飞报告与语音报告
2. 真实课堂脱敏 CSV、统计报告和教师证明
3. MySQL 8 报告与干净冻结提交
4. 教师浏览器录屏、三轮彩排和七分钟 MP4
5. 重新生成发布清单并归档 SHA-256

当前所有未具备的外部证据保持未完成状态，不用本地规则、Mock、合成学生或静态截图替代。
