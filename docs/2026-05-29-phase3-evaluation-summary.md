# 2026-05-29 第三阶段：学习评估系统沉淀

## 完成范围

### P0 统一错题

- 表 `student_mistakes` + [`MistakeService`](backend/app/services/mistake.py)
- 选择题错答自动入库；编程试炼 `POST /student/code-trial/runs`；紧急任务错题入库
- `GET /student/mistakes`、`GET /teacher/students/:id/mistakes`

### P1 效果评估

- [`EvaluationService`](backend/app/services/evaluation.py)
- `GET /student/learning-report`、`GET /teacher/students/:id/learning-report`、`GET /teacher/class-evaluation`
- 紧急任务薄弱点优先读错题本

### P2 导出与大盘

- `GET /teacher/class-export` CSV
- 管理员 `dashboard.weak_knowledge_top`

### 前端

- `studentMistakes.ts`、`learningReport.ts`
- 探索档案学习报告、Explorer 知识 Tab 学情、驿站/星轨接服务端错题与推荐
- 教师领航总览导出 CSV 链接

## 验证

```bash
cd backend
python -m unittest discover -s tests -p "test_mistakes.py" -v
python -m unittest discover -s tests -p "test_evaluation.py" -v
```

## 手测建议

1. 学生答错教师试炼题 → 驿站可见错题 → 紧急任务聚焦该知识点
2. 星轨编程题未通过 → 刷新后驿站仍显示（跨设备）
3. `/student/archives` 学习报告与 `/student/control` 雷达口径一致
4. 教师导出 CSV 含学情字段
