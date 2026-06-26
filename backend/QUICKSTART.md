# 快速开始指南

## ⚡ 最快启动方式 (30秒)

### Windows 用户

完整前后端一键启动请双击仓库根目录的 **`start.bat`**。

当前目录的 **`backend/start.bat`** 仅启动 Flask 后端。

这个脚本会自动：
1. ✅ 检查并安装前后端依赖
2. ✅ 非破坏性初始化数据库
3. ✅ 启动 Flask 与 Vue
4. ✅ 打开前端页面

然后在浏览器中打开：**http://localhost:5173**

### macOS / Linux 用户

在终端运行：
```bash
chmod +x start.sh
./start.sh
```

---

## 📋 手动启动步骤

如果脚本不工作，按以下步骤手动启动：

### 第 1 步：安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 第 2 步：非破坏性初始化/升级数据库

```bash
python manage.py init
```

该命令对空库创建当前结构并标记迁移版本；对已有库执行增量升级，不删除业务数据。

需要准备两组比赛演示画像时执行：

```bash
python manage.py seed-demo
```

`init_db.py` 会删除所有表，仅限明确需要重置本地演示库时手工执行。

运行两组学生画像、错题反馈、资源生成和教师审核的 API 彩排：

```bash
python scripts/verify_demo_readiness.py
```

脚本使用现有本地数据库并保留彩排记录，不会删除已有数据。

### 第 3 步：启动应用

```bash
python run.py
```

输出示例：
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

然后打开浏览器访问：**http://localhost:5000**

---

## 🧪 测试 API

### 方式 1：使用 curl

#### 注册新用户
```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "email": "test@example.com",
    "password": "password123",
    "real_name": "测试用户",
    "role": "student"
  }'
```

#### 登录
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**返回示例：**
```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "real_name": "管理员",
    "role": "admin",
    "level": 1,
    "total_points": 0,
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresIn": 86400
  }
}
```

#### 获取当前用户信息（需要 Token）
```bash
curl -X GET http://localhost:5000/api/v1/users/me \
  -H "Authorization: Bearer {access_token}"
```

### 方式 2：使用 Postman

1. 下载 [Postman](https://www.postman.com/downloads/)
2. 导入项目文件夹中的 Postman 集合（如果有）
3. 按照提示设置 Token 和参数

### 方式 3：使用 Python

```python
import requests

# 登录
response = requests.post(
    'http://localhost:5000/api/v1/auth/login',
    json={
        'username': 'admin',
        'password': 'admin123'
    }
)

data = response.json()
token = data['data']['access_token']

# 获取用户信息
headers = {'Authorization': f'Bearer {token}'}
response = requests.get(
    'http://localhost:5000/api/v1/users/me',
    headers=headers
)

print(response.json())
```

---

## 🔑 测试账户

初始化后可用的测试账户：

| 角色 | 用户名 | 密码 | 用途 |
|------|--------|------|------|
| 管理员 | `admin` | `admin123` | 系统管理 |
| 教师 | `teacher001` | `teacher123` | 班级管理、教师工作台 |
| 学生 | `student001` | `student123` | 学生操作 |
| 学生 | `student002-005` | `student123` | 学生操作（`init_db` 种子） |
| 学生 | `explorer01`–`explorer10` | `student123` | 李老师班级演示数据（见下方脚本） |

### 批量创建教师班级测试学生

不重置数据库，为 `teacher001` 所属班级创建 10 名 Explorer（含近 7 日委托进度、积分日志、周排名）：

```bash
cd backend
python seed_li_class_students.py
```

账号：`explorer01` … `explorer10`，密码均为 `student123`。可重复执行，已存在用户名会跳过。

### 激励与排名（可选）

扩展成就目录并刷新班级周排名缓存：

```bash
cd backend
python seed_incentive_achievements.py
```

### 试炼演示数据（可选）

在已有李老师班级与学生后，插入进行中/已结束试炼及参与记录：

```bash
cd backend
python seed_trials_demo.py
```

教师 `teacher001` 打开 `/trial-arena` 可见列表与统计；学生 `explorer01` 打开同一路由可参与并完成试炼。

### API 测试

```bash
cd backend
python -m unittest tests.test_trials tests.test_admin_settings tests.test_teacher_student_trials tests.test_student_progress -v
```

### A3 知识库与个性化评测

验证 16 个课程知识点、唯一引用 ID、章节必填项及源文件映射：

```bash
cd backend
python manage.py knowledge-check
python scripts/verify_knowledge_base.py
```

使用固定双画像生成 32 个资源包、160 份本地规则资源，并输出 JSON/CSV：

```bash
python scripts/evaluate_personalization.py --output reports/a3-personalization-local
python scripts/evaluate_profile_extraction.py --output reports/a3-personalization-local/profile-extraction-evaluation.json
python scripts/verify_feedback_loop.py --output reports/a3-personalization-local/feedback-loop-three-rounds.json
```

报告中的 `backend` 固定为 `local_rules`，不得作为真实讯飞模型质量证据。

## 下一阶段证据验证

```bash
python scripts/verify_learning_effect.py
python scripts/verify_security.py
python scripts/verify_performance_recovery.py
python scripts/verify_clean_environment.py
```

报告写入 `reports/a3-next-stage/`。前三项使用隔离测试数据库，不修改演示数据库；干净环境检查读取当前开发数据库并验证健康接口及三个演示账号。

仓库根目录运行 `start.bat --check` 会优先使用 `.venv`，执行数据库升级、演示数据写入和就绪检查，成功返回退出码 `0`，且不会启动服务。

本地若已有旧库，执行 `python manage.py init` 完成非破坏性升级。

---

## ⚙️ 环境配置

`.env` 文件已配置为本地开发使用 SQLite 数据库（无需 MySQL）：

```env
FLASK_ENV=development
FLASK_DEBUG=1
DATABASE_URL=sqlite:///learning_system.db
SERVER_PORT=5000
```

如果要使用 MySQL，修改 `.env`：
```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/learning_system
```

---

## 🐛 常见问题

### Q: 运行时出现 "ModuleNotFoundError"
**A:** 需要安装依赖
```bash
pip install -r requirements.txt
```

### Q: 数据库错误
**A:** 重新初始化数据库
```bash
rm learning_system.db  # 删除旧数据库
python init_db.py      # 重新初始化
```

### Q: 端口 5000 已被占用
**A:** 修改 `.env` 文件中的 `SERVER_PORT` 为其他端口，如 5001

### Q: Token 认证失败
**A:** 确保请求头格式正确
```
Authorization: Bearer <token>
```

---

## 📚 API 文档

完整的 API 文档见：[backend_api_design.md](../backend_api_design.md)

主要模块：
- 🔐 [认证 API](#auth) - 注册、登录、登出
- 👥 [用户 API](#users) - 用户管理、权限
- 📚 [班级 API](#classes) - 班级管理、排名
- 🎖️ [成就 API](#achievements) - 成就、积分
- 🔑 [权限 API](#permissions) - 角色、权限

---

## 🆘 需要帮助？

- 检查 `run.py` 日志输出
- 查看浏览器控制台错误信息
- 确保依赖完整：`pip list`
- 确保端口未被占用：`netstat -an`
