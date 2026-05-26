# 后端API接口设计文档

## 一、API总体设计

### 1. 基础配置
```
服务器地址: http://localhost:5000 (开发环境)
生产环境: https://api.yourserver.com
API版本: v1
响应格式: JSON
认证方式: JWT Token
```

### 2. 请求/响应标准格式

**请求头**：
```
Content-Type: application/json
Authorization: Bearer <token>
```

**成功响应 (200)**：
```json
{
  "code": 0,
  "message": "操作成功",
  "data": {
    // 具体数据
  }
}
```

**错误响应**：
```json
{
  "code": 40001,
  "message": "用户不存在",
  "data": null
}
```

### 3. HTTP状态码规范
| 状态码 | 含义 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（Token过期/无效） |
| 403 | 禁止访问（无权限） |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## 二、数据库表设计

### 核心表结构

#### 1. **users（用户表）**
```sql
CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  phone VARCHAR(20),
  
  # 个人信息
  real_name VARCHAR(50),
  avatar_url VARCHAR(255),
  gender ENUM('male', 'female', 'other') DEFAULT 'other',
  bio TEXT,
  
  # 角色权限
  role_id INT NOT NULL,
  status ENUM('active', 'frozen', 'deleted') DEFAULT 'active',
  
  # 激励系统
  level INT DEFAULT 1,  # Lv1-Lv5
  total_points INT DEFAULT 0,  # 总积分
  consecutive_days INT DEFAULT 0,  # 连续学习天数
  last_learn_date DATE,  # 最后学习日期
  
  # 班级关联
  class_id INT,
  
  # 时间戳
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  
  KEY(role_id),
  KEY(class_id),
  FOREIGN KEY(role_id) REFERENCES roles(id),
  FOREIGN KEY(class_id) REFERENCES classes(id)
);
```

#### 2. **roles（角色表）**
```sql
CREATE TABLE roles (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) UNIQUE NOT NULL,
  description TEXT,
  color VARCHAR(10),  # 配色: student, teacher, admin
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO roles VALUES 
(1, 'student', '学生', 'green'),
(2, 'teacher', '教师', 'orange'),
(3, 'admin', '管理员', 'purple');
```

#### 3. **permissions（权限表）**
```sql
CREATE TABLE permissions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) UNIQUE NOT NULL,
  description TEXT,
  resource VARCHAR(50),  # users, classes, courses
  action VARCHAR(50),    # create, read, update, delete
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# 权限示例
INSERT INTO permissions VALUES 
(1, 'view_users', '查看用户', 'users', 'read'),
(2, 'create_user', '创建用户', 'users', 'create'),
(3, 'edit_user', '编辑用户', 'users', 'update'),
(4, 'delete_user', '删除用户', 'users', 'delete'),
(5, 'manage_classes', '管理班级', 'classes', 'all'),
...
```

#### 4. **role_permissions（角色权限中间表）**
```sql
CREATE TABLE role_permissions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  role_id INT NOT NULL,
  permission_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY(role_id, permission_id),
  FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE,
  FOREIGN KEY(permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);
```

#### 5. **classes（班级表）**
```sql
CREATE TABLE classes (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  grade_level INT,  # 年级
  teacher_id INT NOT NULL,
  
  student_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY(teacher_id) REFERENCES users(id)
);
```

#### 6. **achievements（成就/勋章表）**
```sql
CREATE TABLE achievements (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,        # 勋章名
  description TEXT,
  icon_url VARCHAR(255),             # 勋章图标URL
  rarity ENUM('common', 'rare', 'epic', 'legendary') DEFAULT 'common',
  condition_type VARCHAR(50),        # 获取条件类型
  condition_value INT,               # 条件数值
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# 勋章示例
INSERT INTO achievements VALUES 
(1, '初心者', '完成第一个课程', '/icons/newbie.png', 'common', 'complete_course', 1),
(2, '连续学习者', '连续学习7天', '/icons/streak.png', 'rare', 'consecutive_days', 7),
(3, '全能大师', '完成所有课程', '/icons/master.png', 'epic', 'complete_all', 0),
...
```

#### 7. **user_achievements（用户成就关联表）**
```sql
CREATE TABLE user_achievements (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  achievement_id INT NOT NULL,
  unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE KEY(user_id, achievement_id),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
);
```

#### 8. **points_log（积分日志表）**
```sql
CREATE TABLE points_log (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  points INT NOT NULL,
  reason VARCHAR(100),  # complete_course, daily_task, submission
  related_id INT,       # 关联的课程/任务ID
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### 9. **ranking_cache（排名缓存表）** 
```sql
CREATE TABLE ranking_cache (
  id INT PRIMARY KEY AUTO_INCREMENT,
  class_id INT NOT NULL,
  user_id INT NOT NULL,
  rank INT,
  points INT,
  level INT,
  week VARCHAR(10),  # 2024-w20
  
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY(class_id, user_id, week),
  FOREIGN KEY(class_id) REFERENCES classes(id),
  FOREIGN KEY(user_id) REFERENCES users(id)
);
```

---

## 三、API端点设计

### 1. 认证相关

#### 1.1 用户注册
```
POST /api/v1/auth/register

请求体:
{
  "username": "student001",
  "email": "student@example.com",
  "password": "password123",
  "real_name": "张三",
  "role": "student"  # student | teacher
}

响应:
{
  "code": 0,
  "message": "注册成功",
  "data": {
    "id": 1,
    "username": "student001",
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
}

错误响应:
{
  "code": 40001,
  "message": "用户名已存在"
}
```

#### 1.2 用户登录
```
POST /api/v1/auth/login

请求体:
{
  "username": "student001",
  "password": "password123"
}

响应:
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "id": 1,
    "username": "student001",
    "email": "student@example.com",
    "role": "student",
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "expiresIn": 86400  # 有效期（秒）
  }
}
```

#### 1.3 刷新Token
```
POST /api/v1/auth/refresh

请求体:
{
  "refresh_token": "xxx"
}

响应:
{
  "code": 0,
  "data": {
    "token": "新token",
    "expiresIn": 86400
  }
}
```

#### 1.4 登出
```
POST /api/v1/auth/logout

响应:
{
  "code": 0,
  "message": "登出成功"
}
```

---

### 2. 用户管理

#### 2.1 获取当前用户信息
```
GET /api/v1/users/me

响应:
{
  "code": 0,
  "data": {
    "id": 1,
    "username": "student001",
    "email": "student@example.com",
    "real_name": "张三",
    "avatar_url": "https://...",
    "role": "student",
    
    # 激励系统
    "level": 4,
    "title": "大师学者",
    "total_points": 2850,
    "consecutive_days": 12,
    "achievements_count": 6,
    "class_rank": 2,
    
    # 班级信息
    "class": {
      "id": 1,
      "name": "2024级1班"
    }
  }
}
```

#### 2.2 获取用户列表（管理员/教师）
```
GET /api/v1/users?role=student&class_id=1&page=1&limit=20

查询参数:
- role: student | teacher | admin
- class_id: 班级ID
- status: active | frozen
- page: 页码
- limit: 每页数量
- search: 搜索名字/邮箱

响应:
{
  "code": 0,
  "data": {
    "total": 150,
    "page": 1,
    "limit": 20,
    "users": [
      {
        "id": 1,
        "username": "student001",
        "real_name": "张三",
        "email": "student@example.com",
        "level": 4,
        "total_points": 2850,
        "class_id": 1,
        "status": "active"
      },
      ...
    ]
  }
}
```

#### 2.3 更新用户信息
```
PUT /api/v1/users/:id

请求体:
{
  "real_name": "张三",
  "phone": "13800000000",
  "bio": "热爱学习的学生",
  "avatar_url": "https://..."
}

响应:
{
  "code": 0,
  "message": "更新成功",
  "data": { ... }
}
```

#### 2.4 修改密码
```
PUT /api/v1/users/:id/password

请求体:
{
  "old_password": "oldpwd123",
  "new_password": "newpwd456"
}

响应:
{
  "code": 0,
  "message": "密码修改成功"
}
```

#### 2.5 删除用户（管理员）
```
DELETE /api/v1/users/:id

响应:
{
  "code": 0,
  "message": "用户已删除"
}
```

#### 2.6 冻结/解冻用户
```
PATCH /api/v1/users/:id/status

请求体:
{
  "status": "frozen"  # active | frozen
}

响应:
{
  "code": 0,
  "message": "用户状态已更新"
}
```

---

### 3. 权限管理

#### 3.1 获取角色列表
```
GET /api/v1/roles

响应:
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "name": "student",
      "description": "学生",
      "color": "green",
      "permissions": [1, 2, 3, 4]
    },
    {
      "id": 2,
      "name": "teacher",
      "description": "教师",
      "color": "orange",
      "permissions": [5, 6, 7, 8, 9]
    },
    {
      "id": 3,
      "name": "admin",
      "description": "管理员",
      "color": "purple",
      "permissions": [1,2,3,4,5,6,7,8,9,10,...]
    }
  ]
}
```

#### 3.2 获取权限列表
```
GET /api/v1/permissions?resource=users

响应:
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "name": "view_users",
      "description": "查看用户",
      "resource": "users",
      "action": "read"
    },
    ...
  ]
}
```

#### 3.3 为角色分配权限
```
POST /api/v1/roles/:role_id/permissions

请求体:
{
  "permissions": [1, 2, 3, 5]  # 权限ID列表
}

响应:
{
  "code": 0,
  "message": "权限已更新"
}
```

#### 3.4 检查用户权限
```
GET /api/v1/users/:id/permissions

响应:
{
  "code": 0,
  "data": {
    "user_id": 1,
    "role": "student",
    "permissions": [
      "view_users",
      "edit_self_profile",
      "submit_assignment"
    ],
    "can_manage_classes": false,
    "can_manage_permissions": false
  }
}
```

---

### 4. 班级管理

#### 4.1 创建班级
```
POST /api/v1/classes

请求体:
{
  "name": "2024级1班",
  "description": "2024年入学的一班",
  "grade_level": 1,
  "teacher_id": 5
}

响应:
{
  "code": 0,
  "data": {
    "id": 1,
    "name": "2024级1班",
    "teacher_id": 5,
    "student_count": 0,
    "created_at": "2024-05-09T10:30:00Z"
  }
}
```

#### 4.2 获取班级列表
```
GET /api/v1/classes?teacher_id=5&page=1

响应:
{
  "code": 0,
  "data": {
    "total": 5,
    "classes": [
      {
        "id": 1,
        "name": "2024级1班",
        "description": "2024年入学的一班",
        "teacher_id": 5,
        "teacher_name": "李老师",
        "student_count": 32,
        "created_at": "2024-05-09T10:30:00Z"
      },
      ...
    ]
  }
}
```

#### 4.3 获取班级详情
```
GET /api/v1/classes/:id

响应:
{
  "code": 0,
  "data": {
    "id": 1,
    "name": "2024级1班",
    "teacher": {
      "id": 5,
      "name": "李老师"
    },
    "students": [
      {
        "id": 1,
        "username": "student001",
        "real_name": "张三",
        "level": 4,
        "total_points": 2850,
        "consecutive_days": 12
      },
      ...
    ],
    "total_students": 32,
    "class_stats": {
      "avg_level": 3.2,
      "avg_points": 1650,
      "active_count": 28
    }
  }
}
```

#### 4.4 更新班级信息
```
PUT /api/v1/classes/:id

请求体:
{
  "name": "2024级1班",
  "description": "更新描述"
}

响应:
{
  "code": 0,
  "message": "班级已更新"
}
```

#### 4.5 添加学生到班级
```
POST /api/v1/classes/:id/students

请求体:
{
  "student_ids": [1, 2, 3]  # 单个 或 或 student_ids
}

或

{
  "username": "student001"  # 通过用户名添加单个学生
}

响应:
{
  "code": 0,
  "message": "学生已添加",
  "data": {
    "added_count": 3,
    "failed_count": 0
  }
}
```

#### 4.6 从班级移除学生
```
DELETE /api/v1/classes/:id/students/:student_id

响应:
{
  "code": 0,
  "message": "学生已移除"
}
```

#### 4.7 批量导入学生
```
POST /api/v1/classes/:id/students/import

请求体（FormData）:
- file: CSV/Excel文件
格式: username, email, real_name
示例:
student001, student001@example.com, 张三
student002, student002@example.com, 李四

响应:
{
  "code": 0,
  "message": "导入成功",
  "data": {
    "imported": 30,
    "failed": 2,
    "errors": [
      {
        "row": 5,
        "reason": "邮箱已存在"
      }
    ]
  }
}
```

#### 4.8 删除班级
```
DELETE /api/v1/classes/:id

响应:
{
  "code": 0,
  "message": "班级已删除"
}
```

---

### 5. 激励系统相关

#### 5.1 获取用户等级信息
```
GET /api/v1/users/:id/level

响应:
{
  "code": 0,
  "data": {
    "user_id": 1,
    "current_level": 4,
    "title": "大师学者",
    "title_color": "orange",
    "total_points": 2850,
    "points_to_next_level": 650,
    "progress_percent": 74,
    "consecutive_days": 12,
    "last_learn_date": "2024-05-09",
    "achievements_unlocked": 6,
    "achievements_total": 19
  }
}
```

#### 5.2 获取用户成就/勋章列表
```
GET /api/v1/users/:id/achievements

响应:
{
  "code": 0,
  "data": {
    "user_id": 1,
    "unlocked": [
      {
        "id": 1,
        "name": "初心者",
        "description": "完成第一个课程",
        "icon_url": "/icons/newbie.png",
        "rarity": "common",
        "unlocked_at": "2024-04-10T15:30:00Z"
      },
      ...
    ],
    "locked": [
      {
        "id": 3,
        "name": "全能大师",
        "description": "完成所有课程",
        "progress": "8/10",
        "icon_url": "/icons/master.png",
        "rarity": "epic"
      }
    ]
  }
}
```

#### 5.3 获取班级排名榜
```
GET /api/v1/classes/:id/ranking?week=2024-w20

查询参数:
- week: 周(可选)，不传则为总排名
- limit: 限制数量

响应:
{
  "code": 0,
  "data": {
    "class_id": 1,
    "week": "2024-w20",
    "ranking": [
      {
        "rank": 1,
        "user_id": 1,
        "username": "student001",
        "real_name": "张三",
        "level": 4,
        "total_points": 2850,
        "consecutive_days": 12,
        "rank_change": 2,  # 相比上周变化
        "achievements_count": 6,
        "medal": "🥇"
      },
      {
        "rank": 2,
        "user_id": 2,
        "username": "student002",
        "real_name": "李四",
        "level": 4,
        "total_points": 2650,
        "rank_change": -1,
        "medal": "🥈"
      },
      ...
    ]
  }
}
```

#### 5.4 添加积分（内部接口）
```
POST /api/v1/points/add

请求体:
{
  "user_id": 1,
  "points": 50,
  "reason": "complete_course",  # complete_course, daily_task, submit_assignment
  "related_id": 10  # 关联的课程/任务ID
}

响应:
{
  "code": 0,
  "data": {
    "user_id": 1,
    "new_total_points": 2900,
    "level_up": true,
    "new_level": 4,
    "achievements_unlocked": ["连续学习者"]
  }
}
```

#### 5.5 获取积分日志
```
GET /api/v1/users/:id/points-log?limit=20

响应:
{
  "code": 0,
  "data": [
    {
      "id": 100,
      "points": 50,
      "reason": "complete_course",
      "description": "完成课程《Python基础》",
      "created_at": "2024-05-09T14:30:00Z"
    },
    {
      "id": 99,
      "points": 10,
      "reason": "daily_task",
      "description": "每日签到",
      "created_at": "2024-05-09T08:00:00Z"
    }
  ]
}
```

---

### 6. 班级热力图/统计

#### 6.1 获取班级学习热力图
```
GET /api/v1/classes/:id/heatmap?period=month

查询参数:
- period: week | month | year

响应:
{
  "code": 0,
  "data": {
    "class_id": 1,
    "total_students": 32,
    "active_students": 28,
    "inactive_students": 4,
    "heatmap": [
      {
        "date": "2024-05-01",
        "active_count": 28,
        "inactive_count": 4,
        "avg_learning_time": 45  # 分钟
      },
      ...
    ],
    "summary": {
      "completion_rate": 0.875,  # 87.5%
      "avg_points": 1650,
      "top_student": {
        "id": 1,
        "name": "张三",
        "points": 2850
      }
    }
  }
}
```

#### 6.2 教师工作台聚合（已实现）

```
GET /api/v1/teacher/overview

权限: teacher | admin（JWT + role_required）

查询参数:
- class_id: number（可选，指定班级；教师仅能访问本人负责班级）
- period: week | month（默认 week，影响热力图天数：7 或 30）

响应 data 主要字段:
- teacher: { id, username, real_name, role }
- classes: 班级列表（教师仅返回本人班级，管理员返回全部）
- selected_class: 当前选中班级
- period: week | month
- metrics: { student_count, active_count, frozen_count, avg_points, avg_today_completion, attention_count }
- heatmap: { days: [{ date, label }], rows: [{ user_id, student_name, avg_rate, cells: [{ date, completed, total, rate }] }] }
- ranking: Top 学生周排名（来自 ranking_cache 或积分排序）
- attention_students: 需跟进学生（含 reasons 数组）
- students: 班级学生行（等级、积分、今日委托完成率、排名等）
- recent_activity: 近期积分日志摘要（班级内）

说明: 前端教师端 `/teacher`、`/teacher/starfield`、`/teacher/explorers` 共享该接口；切换班级或周期时重新请求。
```

---

## 四、认证授权流程

### JWT Token结构
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": 1,
    "username": "student001",
    "role": "student",
    "class_id": 1,
    "exp": 1715248200,
    "iat": 1715161800
  },
  "signature": "..."
}
```

### Token有效期
- Access Token: 24小时
- Refresh Token: 7天

### 权限检查流程
```
1. 接收请求 + Authorization Header
2. 验证Token有效性
3. 解析Token获取user_id和role
4. 查询user的role权限
5. 检查action是否在权限列表
6. 允许/拒绝请求
```

---

## 五、错误码对照表

| 错误码 | HTTP状态 | 含义 |
|--------|---------|------|
| 0 | 200 | 成功 |
| 40001 | 400 | 用户不存在 |
| 40002 | 400 | 用户名/邮箱已存在 |
| 40003 | 400 | 密码错误 |
| 40004 | 400 | 参数错误 |
| 40101 | 401 | Token无效/过期 |
| 40301 | 403 | 无操作权限 |
| 40302 | 403 | 无法操作其他用户数据 |
| 40401 | 404 | 资源不存在 |
| 50001 | 500 | 数据库错误 |
| 50002 | 500 | 服务器错误 |

---

## 六、Flask项目结构

```
backend/
├── app/
│   ├── __init__.py              # Flask应用初始化
│   ├── config.py                # 配置管理
│   ├── models/                  # 数据模型
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── permission.py
│   │   ├── class_model.py
│   │   ├── achievement.py
│   │   └── ...
│   ├── routes/                  # API路由
│   │   ├── auth.py              # /api/v1/auth
│   │   ├── users.py             # /api/v1/users
│   │   ├── roles.py             # /api/v1/roles
│   │   ├── classes.py           # /api/v1/classes
│   │   ├── achievements.py      # /api/v1/achievements
│   │   ├── points.py            # /api/v1/points
│   │   └── ...
│   ├── services/                # 业务逻辑
│   │   ├── user_service.py      # 用户业务
│   │   ├── auth_service.py      # 认证业务
│   │   ├── class_service.py     # 班级业务
│   │   ├── achievement_service.py # 成就业务
│   │   ├── ranking_service.py   # 排名业务
│   │   └── ...
│   ├── middleware/              # 中间件
│   │   ├── auth_middleware.py   # JWT认证
│   │   ├── permission_middleware.py  # 权限检查
│   │   └── error_handler.py     # 错误处理
│   └── utils/                   # 工具函数
│       ├── jwt_utils.py         # JWT相关
│       ├── password_utils.py    # 密码加密
│       ├── validators.py        # 数据验证
│       └── decorators.py        # 装饰器
├── migrations/                  # 数据库迁移
├── tests/                       # 测试
├── requirements.txt             # 依赖
└── run.py                       # 启动文件
```

---

## 七、开发优先级

### 第一周
- [x] 数据库表设计
- [ ] Flask项目初始化
- [ ] 认证模块（登录/注册）
- [ ] JWT中间件

### 第二周
- [ ] 用户管理API（CRUD）
- [ ] 权限管理API
- [ ] 班级管理API

### 第三周
- [ ] 激励系统API（等级、积分、勋章）
- [ ] 排名系统API
- [ ] 数据统计API

### 第四周
- [ ] 前后端联调
- [ ] 异常处理完善
- [ ] API文档补充

---

## 八、环境配置示例

### .env 文件
```
FLASK_ENV=development
FLASK_DEBUG=True

# 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DB=learning_system

# JWT
JWT_SECRET_KEY=your_secret_key_here_change_in_production
JWT_EXPIRATION=86400

# 服务器
SERVER_PORT=5000
SERVER_HOST=0.0.0.0
```

### requirements.txt
```
Flask==2.3.0
Flask-SQLAlchemy==3.0.0
Flask-JWT-Extended==4.4.0
PyMySQL==1.0.0
python-dotenv==1.0.0
Werkzeug==2.3.0
marshmallow==3.18.0
```

---

## 九、API测试示例（使用curl）

### 注册
```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student001",
    "email": "student@example.com",
    "password": "password123",
    "real_name": "张三",
    "role": "student"
  }'
```

### 登录
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student001",
    "password": "password123"
  }'
```

### 获取当前用户（需要Token）
```bash
curl -X GET http://localhost:5000/api/v1/users/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### 创建班级（管理员）
```bash
curl -X POST http://localhost:5000/api/v1/classes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "2024级1班",
    "description": "2024年入学的一班",
    "grade_level": 1,
    "teacher_id": 5
  }'
```

---

## 十、安全考虑

### 1. 密码安全
- 使用bcrypt加密存储
- 密码长度最少8位
- 不保存明文密码

### 2. Token安全
- 使用HS256算法
- 设置合理的过期时间
- HTTPS传输

### 3. 权限校验
- 每个端点都检查权限
- 用户只能修改自己的数据（除非是管理员）
- 管理员操作有审计日志

### 4. 数据验证
- 前端校验 + 后端校验
- SQL注入防护
- XSS防护

---

