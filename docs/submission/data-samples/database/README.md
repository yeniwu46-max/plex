# 预置演示数据库

**文件**：`learning_system.db`（SQLite）  
**大小**：9.06 MB  

## 数据概览（打包时快照）

| 指标 | 数量 |
|---|---|
| 数据表 | 35 |
| 用户 | 321 |
| 班级 | 11 |
| 试炼 | 28 |
| 学生画像 | 311 |
| 学习资源 | 4 |

## 演示账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| 管理员 | admin | admin123 |
| 教师 | teacher001 | teacher123 |
| 学生 | student001 | student123 |
| 学生演示 | explorer01 ~ explorer10 | student123 |

## 运行时路径

一键启动时会自动复制到：

`source/backend/instance/learning_system.db`

与 `backend.env.production-ready` 中的 `DATABASE_URL=sqlite:///instance/learning_system.db` 对应。
