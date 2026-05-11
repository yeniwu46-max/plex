# 快速开始指南

## ⚡ 最快启动方式 (30秒)

### Windows 用户

双击运行：**`start.bat`** 文件

这个脚本会自动：
1. ✅ 安装所有依赖
2. ✅ 初始化数据库
3. ✅ 启动应用

然后在浏览器中打开：**http://localhost:5000**

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

### 第 2 步：初始化数据库

```bash
python init_db.py
```

输出示例：
```
删除现有表...
创建新表...
插入初始数据...
数据库初始化完成！
测试账户信息：
  管理员: admin / admin123
  教师: teacher001 / teacher123
  学生: student001 / student123 (学生001-005)
```

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
| 教师 | `teacher001` | `teacher123` | 班级管理 |
| 学生 | `student001` | `student123` | 学生操作 |
| 学生 | `student002-005` | `student123` | 学生操作 |

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
