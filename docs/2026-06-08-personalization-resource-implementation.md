# PLEX 个性化学习核心闭环实现说明

**实现日期**：2026-06-08  
**目标课程**：《Python 程序设计基础》

## 一、已完成能力

### 1. 对话式七维学生画像

画像固定包含：

1. 专业背景
2. 知识基础
3. 学习目标
4. 讲解偏好
5. 易错模式
6. 学习节奏
7. 兴趣方向

系统支持自然语言抽取、低置信度确认、人工修正、行为证据补充、版本号和历史记录。讯飞不可用时返回 `local_rules`，不会伪装为模型结果。

### 2. 五类个性化资源

一次生成任务可持久化生成：

- `lesson_document`
- `mind_map`
- `exercise_set`
- `extended_reading`
- `coding_lab`

可选类型 `audio_explanation` 当前使用明确标记的本地降级内容；讯飞控制台暂未获得语音合成额度。

生成流水线固定为：

1. `profile_interpreter`
2. `knowledge_retriever`
3. `instructional_designer`
4. `resource_generator`
5. `quality_reviewer`
6. `path_planner`

每项资源保存画像快照、难度、预计时间、推荐理由、课程引用、置信度、审核状态、实际后端和生成智能体。

### 3. 异步进度与审核

- 进程内执行器最多并行两个任务。
- 测试环境同步执行，保证测试确定性。
- 状态为 `pending/running/completed/failed`。
- 记录单调递增进度、当前智能体、步骤耗时、失败原因和重试来源。
- 超时运行任务会转为可重试失败。
- 低置信度、缺少引用或引用不在课程白名单内的资源进入 `pending_review`。
- 学生只能看到 `approved` 资源，教师可批准或驳回。

### 4. 学习闭环

推荐与学习路径响应已增加：

- `profile_version`
- 推荐资源 ID
- 推荐理由
- 画像更新建议

错题和薄弱知识点会参与画像建议、路径和资源推荐计算；已确认的学习目标和兴趣不会被行为证据直接覆盖。

### 5. 课程知识库

`backend/data/rag_docs/python-basics/` 已完成 4 个模块、16 个知识点。每个知识点包含概念、正反示例、常见错误、基础题、进阶题和来源。

## 二、新增接口

### 学生画像

- `GET /api/v1/student/profile`
- `POST /api/v1/student/profile/chat`
- `PUT /api/v1/student/profile`
- `GET /api/v1/student/profile/history`

### 个性化资源

- `POST /api/v1/student/resource-generation/tasks`
- `GET /api/v1/student/resource-generation/tasks/<task_id>`
- `POST /api/v1/student/resource-generation/tasks/<task_id>/retry`
- `GET /api/v1/student/personalized-resources`

### 教师审核

- `GET /api/v1/teacher/personalized-resources/review`
- `PUT /api/v1/teacher/personalized-resources/<id>/review`

## 三、前端入口

- 学生画像：`/student/profile`
- 个性化资源中心：`/student/resources`
- 教师资源审核：`/teacher/resources`

资源中心通过轮询显示任务进度、智能体步骤、实际后端、降级原因、置信度和引用。内容使用文本方式安全展示，未直接注入模型 HTML。

## 四、讯飞配置

本地 `backend/.env` 配置：

```env
IFLYTEK_SPARK_API_PASSWORD=
IFLYTEK_SPARK_MODEL=lite
IFLYTEK_SPARK_URL=https://spark-api-open.xf-yun.com/v1/chat/completions
```

密钥不得写入 Git。无密钥、超时或非法 JSON 时自动降级为本地规则/课程模板，并在接口和界面中标明实际后端。

## 五、数据库升级

新增迁移：

`backend/migrations/versions/20260609_0003_personalization.py`

项目历史首个 Alembic 版本是已有数据库的基线标记，不负责从空库创建全部旧表。因此：

- 全新环境：按现有应用启动流程由 `db.create_all()` 创建当前完整结构。
- 已有环境：确认数据库已处于 `20260530_0002` 基线后，升级到 `20260609_0003`。

已使用 SQLite 完成“旧结构基线 → 新版本”的迁移冒烟验证。

## 六、验证结果

- 后端全量测试：`55 passed`
- 前端生产构建：通过
- 新增 Python 模块静态编译：通过
- 个性化迁移冒烟测试：通过
- 课程知识点：4 个模块、16 个知识点

前端构建仍有第三方 `PURE` 注释和大 chunk 警告，不影响当前产物，可在功能冻结后单独优化。

## 七、尚未完成的比赛交付工作

以下不是核心代码缺失，但必须在 6 月 24 日至 30 日继续完成：

- 使用真实讯飞凭证完成联网成功、超时和降级演示留证。
- 准备两组差异明显的学生画像和对应五类资源截图。
- 完成三角色完整演示两次，并记录阻断问题。
- 补齐开发说明、测试说明、部署说明、开源许可证和 AI Coding 使用说明。
- 制作 PPT、架构图、7 分钟视频脚本并录制最终视频。
- 在全新机器或干净环境执行一次完整部署。

