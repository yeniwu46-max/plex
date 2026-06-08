# 学生画像与个性化资源接口草案

**状态**：2026-06-08 契约草案，6 月 22 日实现前冻结
**范围**：《Python 程序设计基础》单课程

## 设计原则

- 画像不少于 7 维，既包含对话抽取信息，也包含学习行为证据。
- 学生可确认和修改模型抽取结果。
- 资源生成任务必须可查询进度、失败原因和实际生成后端。
- 正式资源必须包含知识库引用、置信度和审核状态。
- 低置信度内容不能自动发布为班级正式资源。
- API 继续使用 `/api/v1`、JWT 和现有统一响应格式。

## 一、学生画像

### 画像字段

```json
{
  "user_id": 1,
  "dimensions": {
    "major_background": {
      "value": "计算机科学，大一",
      "confidence": 0.96,
      "evidence": ["学生对话：我是计算机专业大一学生"],
      "source": "conversation"
    },
    "knowledge_foundation": {
      "value": "了解变量和输入输出，循环掌握较弱",
      "confidence": 0.91,
      "evidence": ["循环结构近 7 日正确率 35%"],
      "source": "mixed"
    },
    "learning_goal": {
      "value": "两周内完成 Python 基础并能编写小程序",
      "confidence": 0.9,
      "evidence": ["学生对话"],
      "source": "conversation"
    },
    "explanation_preference": {
      "value": "案例优先、分步骤讲解",
      "confidence": 0.86,
      "evidence": ["学生偏好确认"],
      "source": "confirmed"
    },
    "mistake_pattern": {
      "value": "循环边界和列表下标错误",
      "confidence": 0.94,
      "evidence": ["错题本和代码运行记录"],
      "source": "behavior"
    },
    "learning_pace": {
      "value": "每日 30 分钟，适合小步任务",
      "confidence": 0.82,
      "evidence": ["学生对话和委托完成时长"],
      "source": "mixed"
    },
    "interest_direction": {
      "value": "数据处理和小游戏",
      "confidence": 0.88,
      "evidence": ["学生对话"],
      "source": "conversation"
    }
  },
  "completion_rate": 100,
  "version": 3,
  "updated_at": "2026-06-23T10:00:00+08:00"
}
```

`source` 固定为：

- `conversation`
- `behavior`
- `mixed`
- `confirmed`

### `GET /api/v1/student/profile`

返回当前学生完整画像。没有画像时返回空维度、`completion_rate: 0` 和引导提示，不返回 404。

### `POST /api/v1/student/profile/chat`

请求：

```json
{
  "message": "我是计算机专业大一学生，每天能学习半小时，希望多看代码示例。",
  "conversation_id": "optional-id",
  "confirm_changes": false
}
```

响应数据：

```json
{
  "conversation_id": "pc_xxx",
  "assistant_reply": "已识别你的专业背景、学习节奏和讲解偏好，请确认。",
  "proposed_changes": [
    {
      "dimension": "learning_pace",
      "old_value": null,
      "new_value": "每日 30 分钟，适合小步任务",
      "confidence": 0.91,
      "evidence": ["每天能学习半小时"],
      "requires_confirmation": false
    }
  ],
  "profile": {},
  "backend": "iflytek_spark",
  "safety": {
    "passed": true,
    "flags": []
  }
}
```

规则：

- 单字段置信度低于 `0.75` 时必须确认。
- `confirm_changes: false` 时只返回建议，不持久化低置信度字段。
- 行为数据不得覆盖学生已明确确认的目标和兴趣，只能提出更新建议。

### `PUT /api/v1/student/profile`

允许学生确认或人工修改画像字段。

请求：

```json
{
  "changes": {
    "explanation_preference": "先给例子，再解释概念"
  },
  "reason": "student_correction"
}
```

人工修改后的字段标记为 `source: confirmed`。

### `GET /api/v1/student/profile/history`

查询画像版本和变更来源，支持 `page`、`page_size`。

## 二、个性化资源

### 资源类型

固定枚举：

- `lesson_document`：课程讲解文档
- `mind_map`：知识图谱或思维导图
- `exercise_set`：分层题库
- `extended_reading`：拓展阅读
- `coding_lab`：代码实操案例
- `audio_explanation`：语音讲解

### 资源对象

```json
{
  "id": 101,
  "user_id": 1,
  "knowledge_key": "loop",
  "knowledge_label": "循环结构",
  "resource_type": "coding_lab",
  "title": "用循环统计每日学习时长",
  "content": "Markdown 或结构化 JSON",
  "content_url": null,
  "difficulty": 35,
  "estimated_minutes": 20,
  "profile_snapshot": {
    "explanation_preference": "案例优先",
    "learning_pace": "每日 30 分钟"
  },
  "recommendation_reason": "近期循环边界错误较多，且偏好代码案例。",
  "citations": [
    {
      "document_id": "python-stage2-loop",
      "title": "控制结构：循环",
      "section": "range 边界",
      "snippet": "range 的结束值不包含在序列中"
    }
  ],
  "confidence": 0.91,
  "review_status": "approved",
  "generator_agent": "resource_generator",
  "generation_task_id": "rg_xxx",
  "backend": "iflytek_spark",
  "created_at": "2026-06-24T10:00:00+08:00"
}
```

`review_status` 固定为：

- `pending_review`
- `approved`
- `rejected`

## 三、生成任务

### `POST /api/v1/student/resource-generation/tasks`

请求：

```json
{
  "knowledge_key": "loop",
  "resource_types": [
    "lesson_document",
    "mind_map",
    "exercise_set",
    "extended_reading",
    "coding_lab",
    "audio_explanation"
  ],
  "force_regenerate": false
}
```

响应：

```json
{
  "task_id": "rg_xxx",
  "status": "pending",
  "progress": 0,
  "current_agent": null,
  "backend": "iflytek_spark",
  "created_at": "2026-06-24T10:00:00+08:00"
}
```

同一学生、知识点和资源类型存在运行中任务时返回现有任务，不重复创建。

### `GET /api/v1/student/resource-generation/tasks/<task_id>`

```json
{
  "task_id": "rg_xxx",
  "status": "running",
  "progress": 55,
  "current_agent": "resource_generator",
  "steps": [
    {"agent": "profile_interpreter", "status": "completed", "latency_ms": 420},
    {"agent": "knowledge_retriever", "status": "completed", "latency_ms": 180},
    {"agent": "instructional_designer", "status": "completed", "latency_ms": 610},
    {"agent": "resource_generator", "status": "running", "latency_ms": null},
    {"agent": "quality_reviewer", "status": "pending", "latency_ms": null},
    {"agent": "path_planner", "status": "pending", "latency_ms": null}
  ],
  "resources": [],
  "error": null,
  "backend": "iflytek_spark"
}
```

任务状态固定为：

- `pending`
- `running`
- `completed`
- `failed`

进度必须单调递增，失败时保留最后进度和失败步骤。

### `POST /api/v1/student/resource-generation/tasks/<task_id>/retry`

仅允许重试当前学生自己的失败任务。重试创建新任务，并返回 `retry_of`。

### `GET /api/v1/student/personalized-resources`

查询参数：

- `knowledge_key`
- `resource_type`
- `review_status`
- `page`
- `page_size`

学生默认只能看到 `approved` 资源和属于自己的个性化资源。

## 四、推荐与路径联动

现有 `/api/v1/student/recommendations` 增加：

```json
{
  "personalized_resources": [],
  "profile_version": 3,
  "recommendation_context": {
    "weak_knowledge": ["loop"],
    "preferred_resource_types": ["coding_lab", "mind_map"],
    "daily_minutes": 30
  }
}
```

现有 `/api/v1/student/learning-path` 的节点增加：

```json
{
  "recommended_resource_ids": [101, 102],
  "recommendation_reason": "循环结构为当前薄弱点，先完成代码案例再做分层题库。"
}
```

## 五、错误与降级

- 输入包含违规内容：`400`，业务码 `40010`。
- 超出 Python 课程范围：`400`，业务码 `40011`。
- 资源任务不存在或不属于当前学生：`404`。
- 讯飞超时：任务转为本地规则后端，并记录 `fallback_reason`。
- 本地规则也失败：任务状态 `failed`，保留可读错误，不返回密钥或内部堆栈。
- 低置信度资源：保存为 `pending_review`，不进入学生正式推荐。

## 六、实现验收

- 7 个画像维度均可由对话或行为证据构建。
- 学生可确认和修正画像。
- 一次任务可生成五类正式资源及语音资源。
- 两种不同画像对同一知识点的资源存在可解释差异。
- 任务进度、实际后端、引用、置信度和审核状态可查询。
- 错题变化能够影响画像建议、路径和资源推荐。
