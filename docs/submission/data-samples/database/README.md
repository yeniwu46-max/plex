# 预置可运行数据库快照

**文件**：`learning_system.db`（SQLite）  
**来源**：打包时本地正在使用的 `mysql+pymysql` 数据库  
**大小**：10.19 MB  
**完整性检查**：`ok`

## 数据概览（打包时快照）

| 指标 | 数量 |
|---|---:|
| 数据表 | 41 |
| 用户 | 311 |
| 班级 | 9 |
| 试炼 | 17 |
| 学生画像 | 309 |
| 题目 | 0 |
| 题目提交 | 0 |
| 学习资源 | 4 |

## 演示账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| 管理员 | admin | admin123 |
| 教师 | teacher001 | teacher123 |
| 学生 | student001 | student123 |
| 学生演示 | explorer01 ~ explorer10 | student123 |

首次一键启动时会复制到 `source/backend/instance/learning_system.db`；后续启动不会覆盖，使用过程中新增的数据会被保留。
