# 学习系统后端 API

一个基于 Flask 的完整后端 API 系统，包含用户认证、班级管理、权限控制和成就系统。

## 功能模块

- **认证模块**：注册、登录、Token 刷新、登出
- **用户管理**：用户信息、权限查询、密码修改
- **班级管理**：班级创建、学生管理、班级排名
- **权限系统**：角色管理、权限分配、权限检查
- **成就系统**：成就管理、积分系统、排名缓存

## 项目结构

```
backend/
├── app/
│   ├── __init__.py           # 应用工厂
│   ├── config.py             # 配置文件
│   ├── models/               # 数据库模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── permission.py
│   │   ├── role_permission.py
│   │   ├── class_model.py
│   │   ├── achievement.py
│   │   ├── user_achievement.py
│   │   ├── points_log.py
│   │   └── ranking_cache.py
│   ├── services/             # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── class_service.py
│   │   ├── permission.py
│   │   └── achievement.py
│   ├── routes/               # 路由层
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── classes.py
│   │   ├── permissions.py
│   │   └── achievements.py
│   ├── middleware/           # 中间件
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── error_handler.py
│   └── utils/                # 工具函数
│       ├── __init__.py
│       ├── decorators.py
│       ├── jwt_utils.py
│       └── response.py
├── migrations/               # 数据库迁移
├── init_db.py               # 数据库初始化脚本
├── run.py                   # 应用入口
├── requirements.txt         # 依赖包
└── .env.example            # 环境变量示例
```

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件配置数据库连接等信息。

### 3. 初始化数据库

```bash
python init_db.py
```

### 4. 运行应用

```bash
python run.py
```

应用将在 `http://localhost:5000` 启动。

## API 文档

详见 `backend_api_design.md` 文件。

## 核心 API 端点

### 认证

- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/logout` - 用户登出
- `POST /api/v1/auth/refresh` - 刷新 Token

### 用户

- `GET /api/v1/users/me` - 获取当前用户
- `GET /api/v1/users` - 获取用户列表
- `GET /api/v1/users/<id>` - 获取用户详情
- `PUT /api/v1/users/<id>` - 更新用户信息
- `PUT /api/v1/users/<id>/password` - 修改密码
- `DELETE /api/v1/users/<id>` - 删除用户
- `PATCH /api/v1/users/<id>/status` - 更新用户状态

### 班级

- `POST /api/v1/classes` - 创建班级
- `GET /api/v1/classes` - 获取班级列表
- `GET /api/v1/classes/<id>` - 获取班级详情
- `PUT /api/v1/classes/<id>` - 更新班级
- `DELETE /api/v1/classes/<id>` - 删除班级
- `POST /api/v1/classes/<id>/students` - 添加学生
- `DELETE /api/v1/classes/<id>/students/<user_id>` - 移除学生
- `GET /api/v1/classes/<id>/ranking` - 获取班级排名

### 权限和角色

- `GET /api/v1/roles` - 获取角色列表
- `GET /api/v1/permissions` - 获取权限列表
- `POST /api/v1/roles/<id>/permissions` - 分配权限

### 成就

- `POST /api/v1/achievements` - 创建成就
- `GET /api/v1/achievements` - 获取成就列表
- `POST /api/v1/achievements/unlock` - 解锁成就
- `GET /api/v1/achievements/user/<id>` - 获取用户成就
- `POST /api/v1/achievements/points` - 添加积分
- `GET /api/v1/achievements/points-log/<user_id>` - 获取积分日志

## 测试账户

初始化数据库后，可以使用以下账户登录：

- **管理员**: username=`admin`, password=`admin123`
- **教师**: username=`teacher001`, password=`teacher123`
- **学生**: username=`student001`, password=`student123` (学生001-005)

## 响应格式

### 成功响应

```json
{
  "code": 0,
  "message": "操作成功",
  "data": { /* 具体数据 */ }
}
```

### 错误响应

```json
{
  "code": 40001,
  "message": "错误信息",
  "data": null
}
```

## 开发注意事项

- 所有需要认证的端点都需要在请求头中包含 JWT Token
- Token 格式：`Authorization: Bearer <token>`
- Token 有效期为 24 小时
- 刷新 Token 有效期为 7 天
