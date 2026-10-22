# 后端API接口设计文档

> 2026-10-14 账号流程增量：注册字段校验、密码找回、会话撤销、OAuth 身份验证及邮件配置见 [账号试用准备说明](docs/2026-10-14-auth-trial-readiness.md)。本地后端默认端口为 5100。

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

#### 6.3 试炼中枢（已实现）

**数据表**

- `trials`：教师按班级发布试炼（`status`: `draft` | `running` | `ended`）
- `trial_participations`：学生参与记录（`status`: `joined` | `completed` | `abandoned`），`(trial_id, user_id)` 唯一

**教师端**

```
GET /api/v1/teacher/trials?class_id={id}
权限: teacher | admin

响应 data:
{
  "trials": [{ "id", "title", "trial_type", "status", "participant_count", "completion_rate", ... }],
  "summary": { "running_count", "total_participants", "avg_completion_rate", "total_reward_points" }
}
```

```
POST /api/v1/teacher/trials
权限: teacher | admin

请求体（JSON）:
{
  "class_id": 1,
  "title": "动态规划挑战赛",
  "trial_type": "solo",
  "knowledge_key": "dp",
  "difficulty": 78,
  "duration_minutes": 60,
  "reward_points": 40,
  "status": "running"   // 可选，默认 running
}
```

```
PATCH /api/v1/teacher/trials/{id}
权限: teacher | admin（仅能修改本人班级/本人创建的试炼）

请求体: { "status": "ended", "title": "...", "starts_at": "...", "ends_at": "..." }
```

```
POST /api/v1/teacher/trials/{id}/publish
权限: teacher | admin

将 draft / scheduled 试炼发布；若 starts_at 在未来则保持 scheduled，否则进入 running。
```

创建试炼 `publish_mode`：`now` | `draft` | `scheduled`；可选 `start_delay_minutes`、`starts_at`。
状态流转：draft → scheduled/running → ended（到期自动结束）。

**学生端**

```
GET /api/v1/student/trials
权限: student

响应 data.trials: 本班 status=running 的试炼，含 my_status、my_score
```

```
POST /api/v1/student/trials/{id}/join
GET /api/v1/student/trials/arena
权限: student

响应: 本班 running + scheduled 试炼（探索舱地图用）

POST /api/v1/student/trials/{id}/complete
权限: student（须本班且试炼为 running）

complete 请求体: { "score": 88 }  // 可选
完成时写入 trial_participations 并记 PointsLog（source=trial）
```

说明: 前端 `/trial-arena` 经 `TrialArenaEntry` 按角色分流 — 教师见 `TrialArenaView`，学生见 `StudentTrialView`。本地演示数据：`python seed_trials_demo.py`（需先 `seed_li_class_students.py`）。

```
GET /api/v1/teacher/students/{student_id}/trials
权限: teacher | admin（仅本人班级学生）

响应 data: { student_id, participations: [{ ...part, trial: {...} }], summary }
```

#### 6.4 控制中枢配置（已实现）

表 `system_settings`：`class_id` 为空为全局默认，否则为班级覆盖。

```
GET /api/v1/admin/settings?class_id=
PUT /api/v1/admin/settings
权限: admin | teacher（教师仅本人班级）

请求体: { "class_id": 1, "settings": { "rules": {...}, "ai_strategies": [...], "notices": [...] } }
```

#### 6.5 学生星轨与档案洞察（已实现）

```
GET /api/v1/student/learning-path
GET /api/v1/student/archive-insights
GET /api/v1/student/dashboard-extras
权限: student

说明: 由试炼完成记录、每日委托进度、积分等推导星域进度与技能分布；供 `/star-path`、`/archives`、学生首页试炼入口使用。

#### 6.6 激励与排名闭环（已实现）

核心服务 `IncentiveService.record_points` / `process_user_incentive`：

1. 写入 `points_log` 并累加 `users.total_points`
2. 按阈值推算 `users.level`（Lv1–Lv5）
3. 扫描 `achievements` 条件并写入 `user_achievements`
4. 刷新 `ranking_cache`（按 ISO 周汇总本周 XP）

`GET /api/v1/users/me` 返回 `level_profile`、`incentive`（班级排名、本周 XP、下一批成就进度）。

完成试炼、每日委托领奖等接口在响应中带 `incentive` 字段（升级、新成就、排名变化）。

种子：`python seed_incentive_achievements.py`
```

#### 6.7 学习评估与错题本（第三阶段）

表 `student_mistakes`：`user_id`, `source`（`mcq` | `code_trial` | `emergency`）, `knowledge_key`, `question_ref`, `fail_count`, `last_failed_at`, `last_passed_at`, `meta`（JSON）。

**学生端**

```
GET /api/v1/student/mistakes?knowledge_key=&active_only=true
POST /api/v1/student/code-trial/runs
GET /api/v1/student/learning-report?period=7d|30d
```

`POST code-trial/runs` 请求体：`question_id`, `question_title`, `knowledge_key`, `topic`, `tags`, `star_path_node_id`, `cases[]`（`label`, `passed`, `error`）。

**教师端**

```
GET /api/v1/teacher/students/{id}/mistakes
GET /api/v1/teacher/students/{id}/learning-report?period=7d|30d
GET /api/v1/teacher/class-evaluation?class_id=&period=7d|30d
GET /api/v1/teacher/class-export?class_id=&format=csv
```

`learning-report` 响应含：`summary`（探索指数、等级文案）、`domain_mastery[]`（含周环比 `delta`）、`mistake_highlights[]`、`trend`、`radar`、`risk_tags`、`recommendations[]`。

**管理员**：`GET /api/v1/admin/dashboard` 增加 `weak_knowledge_top`（全校薄弱知识点 TOP3）。

选择题答错时由 `AssignmentService.submit_answer` 自动写入错题本；紧急任务未全对时写入 `emergency` 来源错题。

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
# 个性化学习核心接口（2026-06-08 增补）

学生画像：

- `GET /api/v1/student/profile`
- `POST /api/v1/student/profile/chat`
- `PUT /api/v1/student/profile`
- `GET /api/v1/student/profile/history`

个性化资源：

- `POST /api/v1/student/resource-generation/tasks`
- `GET /api/v1/student/resource-generation/tasks`
- `GET /api/v1/student/resource-generation/tasks/<task_id>`
- `POST /api/v1/student/resource-generation/tasks/<task_id>/retry`
- `GET /api/v1/student/personalized-resources`
- `GET /api/v1/teacher/personalized-resources/review`
- `PUT /api/v1/teacher/personalized-resources/<id>/review`

画像闭环：

- `GET /api/v1/student/profile/suggestions`
- `PUT /api/v1/student/profile/suggestions/<id>`，请求 `action` 仅允许 `accepted` 或 `rejected`

健康检查：

- `GET /api/v1/health`
- `GET /api/v1/system/ai-health`

生成资源统一返回 `backend`、`citations`、`confidence`、`review_status`、`risk_reasons`、`generator_agent`、`generation_task_id` 和 `profile_snapshot`。生成任务增加 `profile_version`、`request_fingerprint` 和 `recoverable`。详细实现见 `docs/2026-06-09-engineering-stability.md`。

## 十一、学习效果与安全接口（2026-06-12）

### 学习效果

- `GET /api/v1/student/learning-effect?task_id=<task_id>`
- `GET /api/v1/teacher/students/<student_id>/learning-effect?task_id=<task_id>`

接口以资源生成任务的 `created_at` 为介入时间，只统计相同 `knowledge_key` 的已完成作答。返回 `before`、`after`、`delta`、画像版本、资源类型、实际后端、介入时间和作答证据 ID。

前后测各至少需要 3 次有效作答。样本不足时 `status` 为 `insufficient_evidence`，所有变化量为 `null`，不得显示虚假提升。教师接口复用班级归属校验，学生与教师端核心指标来自同一服务。

### 课程安全

画像对话、资源生成、驿站问答和知识库查询被拒绝时，`data.reason_code` 使用稳定枚举：`prompt_injection`、`out_of_course_scope`、`sensitive_content`、`invalid_knowledge_key`、`invalid_resource_type` 或 `invalid_request`。

知识库上传、文档列表、状态和解析接口仅允许 `teacher` 或 `admin`。通用上传服务同时检查角色、场景、扩展名、大小和文件签名。


## 首次入驻与账号外观（2026-10-14）

学生本人新增 `GET/PATCH /api/v1/student/onboarding`、`POST /api/v1/student/onboarding/complete` 和 `POST /api/v1/student/onboarding/acknowledge`；登录用户新增 `GET/PATCH /api/v1/users/me/preferences`。登录与 `/users/me` 返回入驻摘要和本人偏好。完整字段、状态机、问卷枚举、事务与迁移说明见 [首次入驻与账号外观](docs/2026-10-14-student-onboarding.md)。
# 2026-10-15：隔离代码执行契约

- `POST /api/v1/code/run`：Python `code` 和 `stdin` 各最多 64 KiB；执行器仅 Docker/Judge0，无宿主机回退。
- `POST /api/v1/code/submit`：1–30 个自测用例，每个必须含 `expected`（空字符串严格比较）；返回 `evidence_scope=self_test`，自测不构成权威掌握证据。
- 基础设施故障统一 HTTP `503`、业务码 `50301`，`data={retryable:true, graded:false, reason:...}`；不完成正式作答、不记成学生错误。
- `time`、`memory` 可为 `null`，表示没有该测量值。不能显示为实测 0。
- `GET /api/v1/code/result/<id>` 不存在持久记录时返回 404，不能生成默认通过结果。
- `GET /api/v1/code/languages` 增加 `execution` 能力说明；`configured` 仅代表选择了适配器，不代表实际执行已验收。
- 正式试炼 `POST /api/v1/student/assignments/<id>/code-submit` 仍只使用服务器保存的题目与用例，忽略客户端传入的通过标记和用例。
## 2026-10-16 学习证据与状态（P1 基础链路）

- `GET /api/v1/student/learner-state`：学生本人 Python 课程状态；返回 `state_version`、`policy_version`、`concepts`、最近 20 条 `changes`、`pending_events` 和 `failed_events`。不接受客户端 user_id；没有可信作答时 `estimate=null`，不回填旧图谱分值。
- `GET /api/v1/teacher/students/<id>/learner-state`：仅任课教师可查看本班学生，越班返回 403。
- `POST /api/v1/student/tutor-responses/<receipt_id>/displayed`：确认当前学生的服务器生成提示已展示，重复请求幂等。提示生成成功本身不计展示；此事件不改变能力估计。
- `/agents/trial-coach` 新增可选 `formalQuestionId`（整数）。绑定正式题目前校验班级归属，返回 `display_receipt_id`；浏览器渲染后发送上述回执。
- `/student/code-trial/runs` 保留兼容响应，返回 `record=null, evidence_scope=self_test`，不再根据客户端用例布尔值写错题、画像或学习状态。正式教师题目提交继续使用服务器测试，判题记录与事件一起提交。
- 状态由持久事件队列异步更新。正常进程约每 3 秒处理；30 秒租约过期可被其他工作进程接管，数据库冲突重算，异常有退避和失败状态。页面显示待处理数，不伪装已同步。
- 学习状态 v1 为启发式规则：独立样本权重 1、已记录提示后样本权重 0.5，平滑分值 `(1 + 独立通过数 + 0.5 × 辅助通过数) / (2 + 独立样本数 + 0.5 × 辅助样本数)`；证据量为零时不计算。`uncertainty` 是样本量代理指标，不是校准概率。提示、自评复习、登录和到期事件不改变作答数。
- `LEARNER_STATE_READ_MODE=shadow` 为共享默认：新状态展示、旧 RAG 读取保持兼容。`evidence` 切换学习上下文、路径、小 E 聊天及快捷选题的状态来源，同一次请求不混用旧图谱掌握分值。本机 `.env.learning.local` 已启用 evidence；旧试炼教练的完整新契约仍属于 P2。

### 误概念候选审核与决策（2026-10-16）

- 状态响应增加 `misconceptions`。每项含 `id`、`concept_id`、`kind`、`label`、`status`、`revision`、`rule_version`、`distinct_questions`、`evidence`、`reviewer_id`、`review_note`、`updated_version` 与 `explanation`。状态枚举为 `candidate/confirmed/mitigated/dismissed`；证据公开事件 ID、题目 ID、观察说明和时间，不公开隐藏测试或修正程序。
- `POST /api/v1/teacher/students/<student_id>/misconceptions/<id>/review`：仅任课教师，其他账号或班级返回 403。正文为 `{"action":"confirm|dismiss|reopen","expected_revision":1,"request_id":"UUID","note":"1–300 字核对说明"}`。成功返回更新后的完整学习状态；同请求 UUID、同正文重试返回现有结果。候选版本过期或 UUID 被用于不同内容返回 HTTP 409、业务码 `40901`；格式错误返回 400。
- 审核事件与候选、全局状态版本、审计在同一事务提交，不改变独立/辅助作答次数。规则不能覆盖教师驳回。不同题目重复信号仍是候选；后续两道独立练习通过可以标为暂时缓解。
- 路径响应增加 `state_source`、`state_version`、`learning_decision`。其中提示、下一题方向和复习动作含相同 `state_version/concept_id/evidence_ids/reason`。`mastery_score` 可为 `null`，表示未知；前端不得格式化为 0%。
- 小 E 聊天（含 SSE `done`）及快捷操作返回 `state_version` 和 `learning_decision`，快捷选题返回同版本 `question_pick.state_version`。这些是教学依据的摘要，不是模型内部思维链。
- 同次读取的状态、概念、候选采用独立数据库快照。MySQL 显式 `REPEATABLE READ`，SQLite 显式只读事务；教师并发审核通过状态行写入锁与版本条件避免覆盖。

### 课程材料发布与引用访问（2026-10-16，P2）

- 文档响应新增 `visibility: private|class|public`、`class_id: int|null`、`published: boolean`；管理 API 附加 `can_manage` 与 `may_publish_public`。新上传默认私有，客户端不能指定系统内置来源。教师只能修改自己上传的文档，管理员可管理所有文档。
- `PATCH /api/v1/knowledge/documents/<id>/access` 接受完整 `{visibility, class_id, published}`。私有必须 `published=false`；班级范围必须传本人任教班级（管理员不限任教）；非班级范围 `class_id=null`；全课程公开仅管理员可设置。格式/范围非法返回 400，文档不存在或无编辑权限统一 404。
- `GET /api/v1/knowledge/publication-classes` 返回 `{items:[{id,name}]}`，教师仅本人任教班级，管理员全部班级。
- 索引 READY 不等于公开：学生检索只使用当前课程、当前版本、已发布的公共或本班材料，不包含教师笔记/答案片段。教师可预览自己的私有材料。检索与文档/来源读取均使用数据库授权，不信任向量 metadata 的权限。
- `GET /api/v1/rag/sources/<chunk_id>?version=N`：重新校验文档范围、发布状态、索引状态、片段类型及版本；来源失效统一 404，非法版本 400。旧客户端省略 version 时仍必须通过当前权限检查。引用返回 `version/chapter/source_page/url`，URL 由服务器生成。
- 教师 `/rag/retrieve` 的 `as_user_id` 仅允许本人班级的学生；管理员可切换学生，不能通过该字段伪装管理员身份。
- 小 E SSE 保留 `stage/delta/done` 事件形状；stage 先返回，正文先完整缓冲与检查，再分段发送；`done.reply` 等于所有正文 delta 拼接。`latency.first_token_ms` 现在记录首段可见正文时间。生成期间来源撤回、版本变化或转班会使本次答案失效，返回重新提问提示且不提供旧材料内容。

### 题目上下文与本人运行引用（2026-10-16，P2）

- `POST /api/v1/student/tutor/context` 仅当前有效学生可用。请求接受 `question_ref`、`formal_question_id`、`question_version`、`code`、`run_id`；正式题目 ID 优先于浏览器别名。身份、班级、题面、帮助权限和版本均由服务器解析，不采信客户端题面、成绩或报错标记。
- 响应包含 `task`、`task_source`、`local_ref`、`code_hash`、`code_lines`、`run`、`formal_result`、`execution_note`。`task` 仅公开题面、选项、概念、固定引用、不可猜测的版本与允许的帮助层级，不返回答案、隐藏测试或修正版。题目/判题依据改变会使旧版本失效。
- 正式题目须属于学生班级且已开放；来自正式试炼的题库副本继承原试炼权限。未公开、跨班、停用或待审核题目返回 404。现存 `gen-`、`class-hard-`、`mock-` 前端模板只保留自测引用，返回 `task=null, task_source=browser_only`，不将浏览器题面升级为服务器事实。
- 学生 `/code/run`、`/code/submit` 可携带相同上下文字段；执行成功后新增 `run_id`、`code_hash`、`question_version` 和 `evidence_scope=self_test`。运行表只保存代码哈希和有长度限制的输出摘要，不保存源码、输入、预期输出或测试脚本。基础设施错误不创建成功运行记录。
- 运行引用必须属于本人并匹配原始代码哈希、题目引用与版本：不存在/他人记录返回 404，不匹配返回 409。正式判题摘要还须匹配当前题目版本和服务器证据事件，旧记录缺少不可变证据时不推断正式结果。
- 试炼创建/更新接受 `tutoring_policy=auto|disabled|concept_only|guided`；仅有该试炼编辑权的教师可修改。`auto` 在进行中的非自主/小组任务关闭辅导，自主练习或已结束任务允许渐进帮助。此策略当前约束绑定本题的教练入口，不代表全站自由聊天已经按考试策略统一管控。
- 兼容 `/agents/trial-coach` 增加 `runId`、`questionVersion`，继续接受 `formalQuestionId`、`exerciseId` 和 `code`。忽略浏览器上传的题面、通过状态、错误文本和对话历史；使用已校验上下文，L3/L4 请求降至该题允许层级（当前最高 L2）。`disabled` 拒绝，`concept_only` 在新模式服务上线前拒绝旧教练调用。生成期间题目、权限或账号状态变化返回 409，不显示旧答案或生成展示回执。
- 当前仍为旧教练兼容输出，增加 `context`；四帮助模式、新 `TutorResponse`、会话请求去重与逐模式输出校验尚待接入，不将本阶段视为完整答案泄露防护。

### 四模式辅导与会话记录（2026-10-16，P2 后续）

- `POST /api/v1/student/tutor/ask`，仅学生本人。请求必须带 UUID `request_id`、`mode=explain_error|review_approach|next_step|pseudocode`；可传 `session_id`、`question`（最多 8000 UTF-8 字节）、`hint_level`（1–4，按服务器权限收紧）以及上一节的题目、代码和运行上下文字段。未知字段、非法枚举或 UUID 返回 400。
- 首次请求由服务器创建会话；后续携带返回的 `session_id`。会话绑定本人及题目引用/版本，换题或题目变更返回 409，须开启新会话。无题目时明确为自主代码/通用问题讨论，不从浏览器描述建立正式题目权限。
- 返回 `request_id/session_id/mode/status/summary/next_step/follow_up/citations/context/state_version/teaching_plan/evidence_status/evidence_notice/policy_result/generation_mode/display_receipt_id`。`status` 为 `ok/needs_context/safe_fallback`。报错解释/思路检查可含 `annotations:[{line,message}]`；伪代码可含 `scope=partial,pseudocode_lines:[{step,explanation}]`，不向其他模式附加这些字段。
- 报错解释需要当前代码与本人匹配的报错运行记录；思路检查需要学生真实描述或代码，按钮标题不算思路。上下文缺失返回 `needs_context`，不调用模型、不发帮助回执。
- 2026-10-19：纯快捷按钮按服务器题目绑定的知识点名称检索；具体追问保留学生问题，不拼接长题面或概念 ID。自由聊天的明确例子指代仍可承接本人已确认展示的上一轮。检索阈值、来源权限和泄题检查保持原约束。
- 审核未通过时，`policy_result.review_failures` 可包含 `answer_leakage/unsupported_claims/citation_mismatch/repeats_hint/policy_violation`，审核结构异常只返回 `invalid_review`；不保存被拒回答或审核器自由文本。已有历史时不再一律要求学生重复描述尝试，回退明确表示本次未能提供可靠新提示。此诊断字段不代表模型质量评分。
- 一次读取学习状态后形成教学动作；课程取材经 `KnowledgeService`，与显式帮助模式分开。`grounded` 表示检索取得课程材料，引用仅支持其标注说明；`insufficient_evidence/retrieval_unavailable` 明确为缺少依据或检索故障，只提供通用帮助。
- 生成 JSON 先校验完整字段、长度、模式允许字段、代码行号、引用白名单及重复提示，再做独立的语义审核调用，检查直接答案、自然语言完整解法、短伪代码、无依据判断和引用支持关系。未通过或审核不可用时丢弃整个候选，用固定的通用核对提示返回 `safe_fallback`。这是分层工程校验，不是完全防泄题或答案正确率保证。
- 所有正文均完成校验后一次返回；新四模式接口当前是同步 JSON，界面等待时显示处理中，不先展示模型草稿。生成期间及重读记录时重新检查题目/权限/全部使用材料的版本，失效返回 409。
- UUID 与原始请求摘要绑定；相同请求重试返回同一已保存结果、同一回执。不同正文复用 UUID 返回 409。会话与请求使用 120 秒租约；并发提问返回 409 提示稍后重试，过期工作不能提交结果。模型调用期间不持有数据库事务。
- `GET /api/v1/student/tutor/turns/<request_id>`：仅本人可恢复已完成记录；每次核对题目权限和材料依赖，未完成/他人记录 404，过期依据 409。浏览器聊天缓存只保留记录编号，恢复正文通过此接口。服务器保留有限最近已确认展示的历史供模型使用，不接收客户端伪造历史；未确认/已撤回材料的回答不进入下一轮。
- 回执、回答及请求完成状态原子提交；`needs_context` 和未产生合格针对性回答的通用回退不创建帮助回执。浏览器实际展示后沿用 `/student/tutor-responses/<id>/displayed` 幂等确认。生成成功、HTTP 重试、取消或窗口不可见均不会自动计为已展示。
- 代码工作区、聊天页共用四模式契约与回答卡；聊天页自由提问、独立 RAG 与资源生成仍待进一步统一教学计划。旧接口接入情况见下节，不能将四模式入口验收扩大为全站入口已完成。

### 旧学生辅导接口兼容（2026-10-16，P2 接续）

- `/agents/trial-coach`、`/agents/trial-feedback`、`/agents/code-hint` 只允许学生调用；`/agents/student-diagnose` 的学生请求也进入 `TutorService`。教师/管理员的原诊断演示保留原流程。旧 `trial-coach` 已不再直接调用原三智能体输出。
- 模式映射：`error_diagnosis → explain_error`；`code_quality/optimization → review_approach`；`custom → next_step`；`trial-feedback/student-diagnose → review_approach`；`code-hint → next_step`。报错模式没有本人运行引用时请求补充上下文，不采信浏览器 `stderr`。
- 兼容 `exerciseId/formalQuestionId/questionVersion/runId/requestId/sessionId/hintLevel/userQuestion` 及其新接口同义字段；同时提供但值冲突返回 400。忽略客户端题面、成绩、用例结论、画像、账号编号及对话历史。题目权限、当前版本、提示层级、引用授权与候选审核均由统一服务完成。
- 新调用方应携带 UUID；旧客户端不带编号时，服务器以账号、接口、实际辅导输入与题目版本生成稳定请求编号。相同旧请求重试返回原结果，不重复调用模型或领取回执；若想发起相同内容的新一轮，请显式传新的 UUID。兼容适配不把旧字段更改视为新权威证据。
- 返回保留旧展示字段，并增加完整 `tutor: TutorResponse`、请求/会话/回执编号。兼容诊断 `confidence=null`、空薄弱点列表表示没有生成能力判定，不能将其显示为 0% 置信度。代码提示的 `annotated_code` 原样返回学生代码，提示在独立 `comments` 中；不把生成文本插回可执行源码。
- 正式代码工作区“请小E看看”直接使用 `/student/tutor/ask` 的思路检查模式和统一回答卡。运行引用只绑定相同代码快照；重试保留 UUID，改代码后标识旧反馈，切题/切账号/重置丢弃迟到回复。题目面板和页面可见后才确认展示。客户端不再在 404 时自动生成本地提示绕过接口拒绝。
- 本节没有迁移自由聊天、`/agent/*` 更早期分散接口、`/agents/code-learning-cycle`、独立 RAG 与资源生成。它们仍属于后续整合范围，不宣称全站已执行统一教学策略。

### 自由聊天统一教学链路（2026-10-16，P2 接续）

- `POST /student/messenger/chat` 与 `/student/messenger/chat/stream` 接受 `message`（兼容 `content`）、UUID `request_id`、`session_id`，以及与四模式接口相同的题目/代码/运行引用。同步与 SSE 共用同一个请求编号与结果；重复请求不会另生成回答。旧客户端缺 UUID 时创建新请求，不保证其网络重发去重；正式前端始终发送并保留 UUID。
- 兼容接收 `history/messages` 但忽略其中内容；模型只使用本人会话中最近六条已确认展示且依据仍有效的记录。恢复继续使用 `/student/tutor/turns/<id>`，不可通过另一个账号的会话或历史扩权。重复材料依赖按片段 ID 和版本去重。
- 服务端用一次有界规则分类选择教学动作，不额外调用分类模型。四个显式按钮保留原契约；自动回复还可能返回 `concept_explain/algorithm_validation/algorithm_trace/learning_overview/clarify`。这些自动动作由聊天入口选择，普通 `/student/tutor/ask` 仍只接受四种显式模式。任务关闭、概念限定及引用权限在自动分类后仍生效，分类不能放宽任务权限。
- `concept_explain` 可以直接讲解概念，`next_step/follow_up` 可为空；可带 `example:{code,explanation}` 或 `null`，代码最多 12 行，以纯文本展示、不会自动执行。`algorithm_validation` 检查前提与边界，不将有限自测当成正确性证明。`algorithm_trace` 带 `trace_input`、最多六条 `trace_steps`，服务端固定补充未逐步执行的 `trace_notice`。目前是说明性推演，不是执行器轨迹。
- 自动生成的概念示例和推演仍通过同一结构与语义审核。中断、审核失败、材料撤回时不展示候选；同步和 SSE 的最终 `reply` 从同一 `TutorResponse` 格式化。SSE 可先发阶段消息，正文全部检查后才分段返回，`done` 包含完整 `tutor`、请求/会话/回执编号、状态版本及实际总耗时。不再返回虚构的目标首字耗时或随机阶段耗时。
- 成长、薄弱点、下一题与复习路线查询由本人正式作答记录、同一次状态快照和已有推荐服务组成，不由模型猜测数据。`evidence_status=learning_records`、`generation_mode=learning_records`；返回 `records_at`，推荐题目可带 `question_pick`。无完成记录时说明证据不足，不能显示成能力为零或已证明进步。
- 自由对话的澄清、规则回退和学情查询也有展示回执以支持服务端历史；其回执类型 `conversation` 只记录展示时间，不追加 `hint_displayed`。审核通过的教学帮助继续使用原求助事件规则。该变化无需新表或迁移。
- 前端自由提问支持附代码和本人自测引用，与四模式共用服务端会话、回答卡和引用读取。切换账号/对话或卸载页面取消客户端流；服务器正在生成的工作可完成并等待原请求重试，但不会自动确认展示。传输中断时移除不完整显示，不发起另一条匿名同步生成。
- 浏览器缓存只保留回答请求编号，包括尚未接收 `done` 的流式消息；刷新后由服务端重新核验依据。移除了自由对话旧的独立模型提示词、未审核规则回退及客户端历史注入路径。显式“生成知识图/文档”工具仍待后续统一，未列入本节已完成范围。
- SSE 不在应用层强制 `Connection: keep-alive`，连接复用由 WSGI 服务和反向代理管理；避免与开发服务器的关闭连接策略冲突，导致流结束后的下一次请求超时。

### 检索查询清理与材料选择（2026-10-16，P2 接续）

- 请求字段保持不变。内部 `QueryUnderstanding` 增加 `retrieval_query` 和 `query_preparation`，用于审查清理后的取材问题与规则；原问题继续用于教学理解和生成。清理只删除有界礼貌/格式分句，不能以图谱扩展词充当问题证据。
- 内部打分保留 `lexical_raw` 与清理后的 `lexical_abs`。覆盖权重使用 `lexical_idf_offset + BM25 IDF`（默认 offset=1），未匹配词仍计入分母；BM25 排序公式和 0.42 的依据判定阈值不变。分值不进入学生来源视图，也不表示答案正确概率。
- 默认在保持文档数量上限的同时去除精确重复正文，置信支持数按正文分组，转载不重复计证据。Python 缩进、字符串空格、操作符与否定不因去重而合并。材料访问与版本规则不变。
- 增加可选 MMR 上下文选择，默认关闭；现有哈希嵌入对照未证明排序收益。使用版本匹配的已有片段向量，不新增嵌入调用；无向量时使用词项重合度。内部 `selection_vector` 不进入来源或调试 JSON。
- 复现集、五组配置对照和限制见 `docs/evaluation/2026-10-16-retrieval-engineering.md`；没有新增 API、表或迁移。


### 早期学生助手、独立 RAG 与代码自测闭环（2026-10-16，P2 接续）

- 学生调用 `/agent/diagnose`、`/agent/recommend-path`、`/agent/analyze-code`、`/agent/generate-feedback`、`/agents/diagnose-learning` 统一进入 `TutorService`。角色和资料归属取自 JWT；浏览器 `user_id`、诊断、成绩、薄弱点、历史及题面不能成为学习证据。教师/管理员原演示接口不属于本次学生教学链路。
- 兼容返回原字段，并增加 `tutor`、`request_id/session_id/display_receipt_id/state_version`；没有能力判定时 `confidence=null`，相关列表为空。学情查询以本人正式记录和一次状态快照回答，不凭客户端字段猜测掌握度。无代码的诊断/路线查询不调用生成模型。
- 接受四模式服务的题目/运行引用和常用驼峰别名。`problem_id` 解析为服务器题库引用；仅传无法唯一确定题目的 `trial_id/task_id` 返回 400。别名冲突、非对象请求、无权题目、版本失效均明确拒绝，不能悄悄退为无题目聊天。
- 本节适配器缺少 UUID 时创建新请求，不保证旧客户端自动重发去重。正式前端函数补充 UUID，调用方需要在网络重试时复用同一编号。相同 UUID 与相同输入返回已保存结果；同编号改变模式、代码、题目、会话或测试内容返回 409。更早的 `TutorCompatibility` 稳定编号规则见对应历史小节，二者不能混淆。
- 学生 `POST /rag/query` 使用同一教学动作与审核服务，但必须有课程依据及经过审核的引用；依据不足时不调用模型补写课程结论，审核后无引用也返回拒答。`answer/sources` 与 `tutor` 一致，`confidence=null`，`confidence_level=UNASSESSED|LOW_CONFIDENCE`，`generation_mode=llm_reviewed|refused`。教师/管理员查询与调试保留原接口行为。学生执行记录存于辅导会话，旧 `log_id` 为 null，尚未接入统一成本观测。
- `POST /agents/code-learning-cycle` 仅学生本人。接受语言、当前代码、1–30 个自测用例、`run_mode=stdout|expression` 及题目引用；先验证输入和权限、领取幂等请求，再隔离执行。不能同时传旧 `run_id`；已有运行应通过四模式入口绑定。运行期间题目或辅导权限改变返回 409，基础设施失败返回可重试 503，不记作答错误。
- 自测结果保存本人运行引用和有长度上限的展示摘要，不保存测试脚本/输入/源码。每项 `expected/actual` 最多 4096 字符、错误最多 1000 字符；被截取时 `truncated=true`。`evidence_scope=self_test`，不会修改正式成绩、掌握度或清除错题。`tutorResponse` 为统一审核输出；`resources.executionDiagram/microFix=null`，不再返回固定的循环图或微修复题。
- 兼容 `learningProfile.loopMastery=unknown`、`loopMasteryScore=null`、`visualPreferenceConfirmed=null`，不把未确认的讲解偏好当成用户画像。执行轨迹只记录实际发生的隔离自测与辅导审核，耗时为实测。旧面板按真实运行结果与统一回答卡渲染。
- 闭环租约为 180 秒，完成响应、运行引用与展示回执可通过同 UUID 恢复；正常重试和并发请求不会重复执行。若进程在执行结束后、最终响应提交前崩溃，租约到期重试可能再次执行隔离自测，不宣称跨崩溃 exactly-once。没有新增迁移；取消传播、实际模型用量、统一资源/文档工具仍在后续范围内。


### 反例挑战：基准、版本与发布硬门槛（2026-10-16，P3 第一阶段）

本节已实现教师提交候选、验证/发布 API 与学生只读题面。后台模型生成、学生反例判题和 Vue 工作台将在后续接入；不得把当前接口清单当成完整挑战功能已经上线。

| 方法与路径（均以 `/api/v1` 开头） | 请求与返回 |
| --- | --- |
| `POST /teacher/counterexample-specifications` | `{request_id:UUID,class_id,specification}`；确认并冻结教师的题意、参考实现和独立测试，返回 `{id,content_hash}` |
| `POST /teacher/counterexample-challenges` | `{request_id:UUID,spec_id,candidate}`；创建首版草稿，返回教师详情 |
| `GET /teacher/counterexample-challenges/<id>` | 当前版本的题意基准、候选、验证报告及最后审核信息；仅创建者/管理员且仍有班级管理权 |
| `POST /teacher/counterexample-challenges/<id>/versions` | `{request_id:UUID,expected_revision,spec_id,candidate}`；创建新版本并撤下旧发布；不覆盖旧版本 |
| `POST /teacher/counterexample-challenges/<id>/validate` | `{request_id:UUID,manifest_hash}`；同步隔离验证，返回 `{id,version_id,manifest_hash,status,report,completed_at}` |
| `POST /teacher/counterexample-challenges/<id>/review` | `action=publish|withdraw`、当前 `manifest_hash`；发布还须 `validation_id/note/checks` |
| `GET /student/counterexample-challenges` | 本班已发布且有效题面 `{items:[...]}`，当前最多 100 项 |
| `GET /student/counterexample-challenges/<id>` | 本人班级的已发布题面；不存在、撤回或跨班返回 404 |

- 教师提交基准需要 `title/statement/concept_id/input_contract/output_contract/reference_code/tests/reference_note/allowed_bug_exceptions`；知识点必须属于现有课程注册表。基准不可原地修改，改变题意/参考实现/测试须创建新基准，再创建挑战新版本。`reference_note` 是教师对基准来源与核对情况的说明，不是系统自动证明参考程序正确。
- 首版输入为 `integer` 或 `integer_array`，输出另支持 `boolean`。整数契约需 `minimum/maximum`；数组还需 `min_items/max_items`。输入整数范围不超过 ±10^6、数组长度不超过 128；输出整数范围不超过 ±10^12。布尔值不当作整数。非法空输入不是反例；允许空数组须显式 `min_items=0`。
- 基准需 3–24 个不同合法输入的 `{input,expected}` 测试，预期输出也必须满足契约。候选字段为 `buggy_code/fixed_code/bug_kind/explanation`；错误类型仅 `loop_boundary/empty_input/duplicate_elements`。代码须为单个 `def solve(data)`，每份最多 16000 UTF-8 字节，支持小规模列表/整数算法的受限 Python 语法。静态语法检查不执行代码，也不能替代沙箱隔离。
- 验证器分别运行参考版、修正版和错误版，每份程序在两次新的隔离执行中运行全部测试，检查结果和运行环境一致性。参考与修正版须通过独立预期结果；错误版须至少一项不同。错误版只有抛出教师显式列入的 `IndexError/ValueError/ZeroDivisionError` 才能把异常计为反例；其他异常、超时、内存/输出限制、协议不符均阻止发布。
- 每个隔离环境只接收当前程序及测试输入，不接收其他实现或预期输出。固定执行脚本与版本、Python 版本、Docker 镜像内容 ID、题意/代码/测试/契约的 canonical-JSON SHA-256、见证输入与差分结果写入教师报告。判断仅针对声明的有限测试，不能当作对所有输入的正确性证明。
- `status=processing|passed|failed|unavailable|superseded`。执行器基础设施错误返回可重试 503，报告标为 unavailable；材料本身失败返回 200 与 failed。相同请求重试返回同一报告；并发重复返回 409；120 秒租约过期后可重试，旧工作不能覆盖新报告。验证期间版本被修改返回 409，旧报告标为 superseded。
- 开始新验证会撤下该版本已有发布。发布必须引用当前版本的最新 passed 报告，并逐项确认 `checks={single_clear_bug:true,statement_consistent:true,explanation_correct:true,difficulty_appropriate:true}`，填写 1–1500 字审核说明。教师和管理员均不能绕过硬门槛，原资源审批/批量放行接口不操作这些独立表。
- 学生题面响应只含 `id/revision/version/title/statement/concept_id/input_contract/output_contract/allowed_bug_exceptions/buggy_code/signature`。不含修正版、参考实现、隐藏测试、见证反例、错误说明或审核报告。题面读取不写学习事件；学生作答接口见下节。
- 新增四表：`counterexample_specs/counterexample_challenges/counterexample_versions/counterexample_validations`；迁移 `20261016_0023`。保留旧版和验证记录，无占位用户、无演示题自动发布。当前教学审核为教师确认；模型辅助教学审核、生成队列/配额、列表分页和审核历史展示仍待后续完善。

### 学生反例提交与解释核对（2026-10-16，P3 接续）

全部路径位于 `/api/v1`，使用 JWT 和统一响应。身份来自登录账号，不接受请求体中的学生 ID。

| 接口 | 契约 |
| --- | --- |
| `POST /student/counterexample-challenges/<id>/attempts` | `{request_id:UUID,revision,version,input,expected_output,explanation}`；`version` 为题面返回的 manifest hash，说明限 1–2000 字 |
| `GET /student/counterexample-challenges/<id>/attempts` | 当前已发布版本、当前验证基准下，本人最近 20 条 `{request_id,status,created_at}`；无他人记录 |
| `GET /student/counterexample-attempts/<request_id>` | 恢复本人的输入、预期、说明与结果；完整结果须题目仍可访问且验证基准一致 |
| `GET /teacher/counterexample-attempts/<request_id>` | 原挑战所属教师或管理员，且学生仍在所管理班级；含内部执行记录和模型用量 |
| `POST /teacher/counterexample-attempts/<request_id>/review` | `{request_id:UUID,expected_revision,verdict:supported\|needs_revision,note}`；说明 1–500 字，追加解释审核历史 |

- 仅接受契约范围内的 JSON 整数、整数数组或输出布尔值；不接收学生可执行代码。输入验证先于执行/作答记录。对本次输入分别运行参考、修正、错误程序各两次，核对重复结果、输出格式、已声明异常和发布时的运行环境。
- 返回状态 `processing/complete/material_issue/unavailable/stale`。完成时返回 `counterexample_found`、`expected_output_correct`、`correct_result/buggy_result`、`evidence_event_id`、`execution_ms` 和 `explanation_review`。两项执行判断互不代替；`graded=true` 仅表示本次输入已核对，不产生班级成绩、积分或正式掌握分。`evidence_scope=submitted_input_only`。
- 相同请求编号/输入重试复用原结果。改变输入/版本返回 409；并发中请求返回 409。租约为 120 秒，过期可恢复，旧工作不能覆盖新结果；不能据此承诺进程故障下绝不重复隔离执行。提交和学习事件同事务保存。
- 执行环境不可用/运行基准变化返回 503 与可重试状态，不写学习事件。执行中撤回题目、改版或变更班级返回 409，不接受迟到结果。材料不一致、非法异常、不稳定输出及资源超限触发 `material_issue`，暂停当前版本；学生只收到题目待核对提示，不记作答错误。
- 被暂停的版本不能重新验证放行。修复须新基准/新版本；历史上暴露问题且在新契约中仍合法的输入，必须加入独立测试集，再通过验证与教学审核。教师题目详情返回最多 10 条当前版本问题摘要，保留所有历史记录。
- 模型只核对学生的原因说明，收到题意、错误程序、本次输入/执行事实和学生说明，不收到修正版或隐藏测试。模型输出严格结构检查，引用必须来自学生原话；不确定、失败或无效输出为 `needs_teacher`。固定反馈文案避免把未审核的自由文本直接显示。模型不改变执行事实；没有有效反例或预期不符时先提示核对输入，不调用解释模型。
- 教师解释核对使用版本比较和独立 UUID，追加审核记录，保留原模型元数据；不能重判执行事实或重复追加学习事件。当前仍为辅助审核意见，不是经验证的解释评分算法。
- 共享状态新增 `counterexample_count/counterexample_success/counterexample_review_due_at`，单独累积边界实践，不进入能力估计与误概念计数。成功后给出一天后的独立迁移练习提醒；之后相同知识点独立正式答对可解除，乱序旧事件不会重新安排已完成的提醒。这是工程调度规则，不是 SM-2 回忆成绩或已验证的最优间隔。
- 新表 `counterexample_attempts/counterexample_explanation_reviews`、版本阻断字段、状态实践字段由迁移 `20261016_0024` 新增。前端入口 `/student/trials/counterexamples/:challengeId?`，按账号只缓存请求编号，答案通过本人接口恢复；切换账号/题目、卸载时取消客户端请求并忽略迟到结果。取消不保证上游工作停止。

### 教师反例工作台与版本追溯（2026-10-16，P3 接续）

页面 `/teacher/counterexamples` 从教师「试炼中枢 → 反例工作台」进入。新增只读接口均为 JWT + teacher/admin 角色，并在服务层复核班级管理权限与题目创建者。

| 接口（均在 `/api/v1` 下） | 返回与约束 |
| --- | --- |
| `GET /teacher/counterexample-challenges?class_id=<id>&page=1` | 当前班级可管理的题目摘要；教师仅自己的题目，管理员可查看该班级全部。20 条一页，含 `items/page/page_size/total` |
| `GET /teacher/counterexample-specifications/<id>` | 本人可管理的不可变基准、班级及内容哈希，可用于恢复已保存基准 |
| `GET /teacher/counterexample-challenges/<id>/versions?page=1` | 20 条一页的版本摘要，倒序，包括哈希、审核说明和材料阻断状态 |
| `GET /teacher/counterexample-challenges/<id>/versions/<revision>` | 指定不可变版本的题意、三份程序、基准与执行报告；`revision` 是所看版本，`current_revision` 是当前版本 |
| `GET /teacher/counterexample-challenges/<id>/attempts?page=1` | 当前班级未删除学生的提交摘要，包含历史题目版本、状态、学生姓名和解释意见来源；20 条一页 |

- 分页参数必须是正整数；`page` 不超过 100000。跨班或非创建教师访问返回 404。学生角色不能读取上述教师接口。
- 教师题目详情新增 `revision` 字段，与旧 `current_revision` 区分。历史版本只读；验证/审核写入继续校验当前 manifest，不接受旧版本报告为新版本放行。
- 教师作答详情增加 `student_name`、提交时不可变的 `task_snapshot` 和最近 20 条 `review_history`；题目修订不会替换历史作答的题面/错误代码。学生转班或账号标为 deleted 后，不再出现在原班列表，直接详情访问也被拒绝。冻结学生的记录保留给本班教师核对。
- 页面提供结构化输入输出范围、3–24 组 JSON 独立预期测试、参考实现、错误/修正程序和教学说明。保存先确认独立基准，再建立未发布版本；修订保存会撤下旧发布。模型候选生成尚未纳入本节完成范围。
- 网络不确定时重复使用原基准/挑战/版本 UUID 与原始快照，不能把用户后改的表单混进原请求。缓存只存按账号和班级隔离的记录编号；基准已保存而候选未找到时，可恢复基准并要求重新补齐候选。尚未点击保存的编辑不会跨刷新保留。
- 执行报告展示见证输入、运行环境和内容哈希。只有当前版本最新执行通过、四项教学确认及审核说明齐全，页面才启用发布；服务端继续执行独立硬门槛。重新验证会撤回发布，不会以旧报告自动重新公开。
- 教师对学生解释追加意见后，界面展示历史说明与固定执行事实。切换账号/班级或离开页面会取消客户端请求并丢弃迟到回复；服务器已经接收的操作仍可能完成，需读取状态恢复。
- 本轮无数据库结构变更，沿用迁移 `20261016_0024`。


### 教师反例候选生成 · 2026-10-16

全部接口使用 `/api/v1` 前缀、JWT 和 teacher/admin 角色校验，并检查任务创建者及班级管理权限。统一返回 `{code,message,data}`。

| 方法与路径 | 请求与返回 |
|---|---|
| POST `/teacher/counterexample-generation-tasks` | `{request_id: UUID, spec_id: UUID, bug_kind}`；返回任务详情。仅使用已确认的独立基准；不接受测试、预期或候选程序字段。 |
| GET `/teacher/counterexample-generation-tasks?class_id=N&page=1` | 本班可管理的任务摘要，20 条/页。 |
| GET `/teacher/counterexample-generation-tasks/:id` | 本人任务详情、阶段审核、实际模型调用及用量记录。管理员仍需可管理该班级。 |
| POST `/teacher/counterexample-generation-tasks/:id/cancel` | 取消 queued/running 的后续阶段；终态返回原状态。已发出的请求可能继续，结果不得推进已取消任务。 |
| POST `/teacher/counterexample-generation-tasks/:id/retry` | `{expected_attempts: 0..2}`；恢复可重试失败阶段。旧重试请求返回当前状态，不再发起一轮。 |

状态为 `queued/running/ready/rejected/failed/cancelled`，阶段为 `generation/validation/pedagogy`。`ready` 意为等待教师最终审核。`retryable` 由后端计算，最多三轮领取；内容拒绝与权限/版本变化不可原地恢复。默认每教师活跃任务上限 2，最近 24 小时新任务上限 10；超额 429。UUID 相同但基准或错误类型不一致返回 409。不存在/无权管理返回 404，失效账号或角色不符 403。

任务详情包括 `spec_hash/challenge_id/version_id/validation_id`、`generation_audit/pedagogy_review/calls`；调用记录保留实际供应商、型号、策略版本、Token 用量及耗时，未返回时用量未知。相关字段只在教师安全域中返回，不增加学生可见解题材料。

教师题目详情增加 `generation` 摘要。`origin=model_generated` 的版本由后台完成隔离验证，手动 validate 返回 409；重新验证需创建人工修订版本。最终 publish 额外要求任务 ready、自动审核 pass 且绑定当前清单哈希/报告，再检查原有的四项教师确认和说明。

实现与恢复说明见 `docs/2026-10-16-counterexample-generation.md`。


### 反例基准补充验证 · 2026-10-16

`POST /teacher/counterexample-specifications` 的 `specification` 增加可选 `verification`。无需新端点或数据库列；设置保存在不可变的基准 JSON 中，并参与基准/候选清单哈希。

```json
{"verification":{"policy_version":"bounded-properties-v1","boundary_checks":true,"properties":["permutation_invariant","append_zero_invariant","concatenation_additive"],"rationale":"按求和定义确认这些关系及合法边界。"}}
```

`policy_version` 必须为当前支持值，`boundary_checks` 必须为布尔值；`properties` 最多五项且不能重复，仅接受 `permutation_invariant/duplicate_invariant/append_zero_invariant/concatenation_additive/result_is_member`；`rationale` 必填 1–1000 字。边界关闭且没有性质、关系不适用于输入输出类型、没有可执行关系均返回 400。边界检查允许空数组时，独立预期测试必须明确包含 `[]`。

不提供该字段时仍规范化为旧 `counterexample-v1`，保持旧内容哈希；提供时为 `counterexample-v2`。修改任何设置须创建新基准与新版本。不能把 `contract_version` 当作客户端可改字段。

教师验证报告新增 `coverage`、`failure_detail`、`execution_batches`、`witness_count`，见证可含 `input_origin=teacher_test/boundary/metamorphic`。`coverage` 中的 `total_inputs/declared_inputs/boundary_inputs/metamorphic_inputs` 是计划数量；`properties` 记录实际完成的逐程序检查和失败数量，提前失败时不表示其他计划已执行。`plan_hash` 用于复现输入与关系，最多展示八个差异见证。范围为 `declared_tests_only` 或 `declared_and_bounded_checks`，均非全输入正确性证明。

性质失败、补充输入上的参考/修正不一致仍使整个验证失败，不能发布。后台生成使用同一门槛和字段；模型无权修改该配置。学生 DTO 不增加这些教师私有字段。


### 固定反例待审草稿库 · 2026-10-17

教师/管理员专用，JWT 与班级管理权限同时检查，统一返回 `{code,message,data}`。读取不会创建基准、题目、验证报告或发布记录。

| 方法与路径（均以 `/api/v1` 为前缀） | 请求与返回 |
|---|---|
| GET `/teacher/counterexample-templates?class_id=N` | 固定目录 `version/catalog_hash/items`；各项含编号、修订、摘要、标题、知识点、错误类型、建议难度及匹配的开发验证摘要。 |
| GET `/teacher/counterexample-templates/:id?class_id=N&content_hash=HASH` | 当前固定内容，包括 `specification/candidate`；客户端摘要过期返回 409，非法编号 400，不存在 404。 |

目录来源始终为 `provenance=ai_assisted_draft`、`human_review_status=pending`，不代表真实教师审阅。开发证据仅在目录摘要、题目摘要和验证器版本相符时附带；不复用为业务题目的发布依据。未登录 401，学生 403，无班级权限 404。

已有创建与修订接口新增可选 `source_template:{id,content_hash}`；服务端校验固定来源后保存 `{id,revision,content_hash}`。内容完全一致使用 `origin=catalog_draft`，有改动为 `catalog_adapted`；无来源的普通手工创建仍为 `teacher_submitted`。修订未提供来源则继承被修订版本；相同请求编号更换来源返回 409。新增题目仍未验证、未发布，须运行当前环境验证并完成四项人工审核。

教师详情增加 `source_template`；学生返回不增加该字段、正确程序、隐藏测试或开发报告。新数据库列由 `20261017_0026` 创建，不自动导入 30 道题。教师工作台只缓存来源编号与摘要，不缓存题目程序和测试。操作、复现与人工审核材料见 `docs/2026-10-17-counterexample-catalog.md`。


### 资源任务的固定学习上下文 · 2026-10-17

现有学生资源生成、列表、详情和重试路径不变。任务响应新增只读 `learning_context`，旧已完成任务为 null。摘要包括：

- `policy_version=resource-learning-context-v1`、`state_source=shadow/evidence`、`state_version`（shadow 为 null）、`profile_version`。
- `context_hash/captured_at/origin`；origin 为 `task_created` 或旧待执行任务首次绑定的 `legacy_execution`。
- `basis/reason/hint_action/exercise_action/review_action/evidence_count/estimate_disclaimer`，来自固定的服务器学习决策，不接受模型或客户端改写。

原始 `context_snapshot` 仅保存在服务器，不通过任务 DTO 返回。年龄基本资料不读取；画像字段受白名单限制，evidence 模式排除旧行为推断。六步 input_summary 保存同一上下文摘要和状态/画像版本，流水线契约更新为 `resource-pipeline-v3`。

任务创建在同一读取事务中固定资料与状态。执行及失败重试复用原上下文、教学选项和真实模型要求；生成不写学习能力状态。无幂等键的近期复用指纹纳入上下文摘要，显式幂等键的既有任务继续保留原依据。客户端传入 context_snapshot/learning_context 不作为生成依据。

上下文失配时任务失败；步骤间及保存前重新检查账号、角色和班级，变化后停止并要求重新创建。迁移 `20261017_0027` 增加可空 JSON 上下文和摘要列；不回填已完成历史任务。详细说明见 `docs/2026-10-17-resource-learning-context.md`。


## 2026-10-17 补充：资源任务的课程证据

资源任务 DTO 新增可空 `course_evidence`，历史记录为空。新记录包含 `status`（`retrieved` / `builtin_only` / `unavailable`）、`message`；当前可用时还包含 `policy_version`、`source_count`、摘要和来源列表。来源为包级输入证据，不代表逐句正确性保证。

资源 `citations` 保留原 `document_id/title/section/snippet`；课程片段额外有 `kind=course_chunk`、`chunk_id`、`version`、`source_page`、`teacher_verified` 和受 JWT/课程权限保护的来源 URL。客户端提交的来源、上下文或身份不作为检索依据。内部 `evidence_manifest` 与内容哈希不进入 DTO。

后续访问失效时，任务仍保留执行状态，但 `course_evidence.status=unavailable`，返回空资源、空步骤、空审核报告及重新生成提示。学生列表与推荐不列出失效资源；教师审核、批量/开发放行和再审核均不能绕过来源权限。历史无清单记录不补造溯源。

涉及课程片段的可选音视频保留文字稿，`media_status=source_protected`，不创建无法撤回的公开媒体 URL。详见 [资源证据说明](docs/2026-10-17-resource-course-evidence.md)。

## 2026-10-17 补充：小 E 文档与知识图的受控生成

学生专用 POST `/student/messenger/tools/learning-document` 与 `/student/messenger/tools/knowledge-graph` 复用 TutorService。请求 `{topic,request_id}`，主题 2–500 字，request_id 为 UUID；兼容 message 别名与旧客户端省略编号。可选 session_id/question_ref/formal_question_id/question_version/code/run_id 按可信题目上下文验证，不接受客户端来源、画像或策略字段。无课程依据、生成或审核失败返回 status=safe_fallback，不以模板产物冒充成功。题目禁止辅导时返回 403。

返回 artifact_id/request_id/session_id/kind/status/title/markdown/mermaid、knowledge、evidence_status/evidence_notice、policy_result 和 learning_context，兼容 topic/backend；illustration 固定为空。图节点与关系经结构检查后由服务器排版。引用只含可公开的来源元数据，不包含内部内容哈希。

新增本人 GET `/student/messenger/tools/artifacts/:request_id` 用于恢复与下载。跨账号或非工具记录返回 404；当前来源/题目权限或版本变化返回 409，不释放旧正文。相同编号重试去重，更换请求返回 409。复用既有 TutorSession/TutorTurn，不新增迁移；生成/下载不产生学习证据。后续读取复核全部输入来源的版本和正文摘要；历史无摘要的记录保持原版本检查。详见 [学习工具说明](docs/2026-10-17-messenger-learning-artifacts.md)。

## 2026-10-17 补充：辅导取消与用量

- POST `/student/tutor/turns/:request_id/cancel`：学生本人 UUID 请求。未开始也可取消，取消凭据按账号保存。返回 `{request_id,status:cancelled,cancelled:true}`；若已完成则 `{status:complete,cancelled:false}`。跨账号已有请求 404，格式错误 400。同编号重试不会撤销取消。
- GET `/student/tutor/usage`：本人 TutorService 汇总，返回 scope=tutor、UTC period_start/reset_at、request_limit/requests_used/requests_remaining、active_requests/concurrency_limit、model_calls/reported_total_tokens/unknown_usage_calls、failed_calls/cancelled_requests、model_latency_ms。cost=null、cost_status=not_priced；未知用量不表示零费用。

新增持久化请求尝试、取消凭据与调用元数据表，迁移 20261017_0029。默认每账号每 UTC 日 80 次尝试、账号并发 2、辅导全局并发 8、同编号最多 3 次尝试，均由 TUTOR_* 环境变量配置。达到限制返回 429；已连接 SSE 通过 status=429 的 error 事件告知。完成请求缓存重放不计新用量，失败重试计尝试。限制和取消同时覆盖聊天、四模式、学习文档、知识图及统一辅导兼容入口，不代表资源/独立 RAG/反例生成已纳入这份汇总。

取消不保证供应商撤销已发出的调用；当前调用的容量与用量保留到返回，阻止后续步骤和结果发布。服务器已完成优先于取消，不撤销历史学习记录。详见 [辅导运行控制说明](docs/2026-10-17-tutor-runtime-controls.md)。


## 2026-10-17 补充：跨入口文本模型用量

- GET `/ai/usage`：学生、教师、管理员的本人汇总，身份取 JWT，不能通过 user_id 查询他人。返回 scope=connected_text_models、audience=self、class_id=null、UTC period_start/reset_at、totals 及 workflows(tutor/resource/rag/counterexample)。
- GET `/teacher/classes/:class_id/ai-usage`：当前班级教师或管理员，返回 audience=class 与 class_id；越权 404，学生角色 403。只统计创建时已绑定该班的资源和反例出题，未绑定班级的记录不回填。
- 每组包含 calls、reported_total_tokens、unknown_usage_calls、failed_calls、unfinished_calls；未知 tokens 不是零费用。cost=null / cost_status=not_priced，排除向量嵌入、语音、图像、视频及未接入的旧调用。
- 学生 RAG 已走 tutor，独立教师/管理员 RAG 归为 rag；RAG 响应新增服务端 request_id。每次实际 HTTP 尝试单独记录，备用供应商和连接超时重试计次，逻辑辅导观测不重复计次。读取超时、连接重置不自动重复 POST。
- 迁移 20261017_0030 新增可空 class_id、prompt_hash 及索引；旧记录保留 null。本文本汇总不改变原 tutor 额度，不代表资源/独立 RAG/班级配额或货币定价已完成。

详见 [模型账本与用量视图](docs/2026-10-17-model-accounting.md)。


## 2026-10-18 补充：资源接纳额度与重试

资源 POST 创建支持账号隔离的 idempotency_key（1–100 字符）。即使 force_regenerate=true 或超过 15 分钟，同编号同正文返回原任务；内容冲突 409。新任务与额度检查在数据库短锁事务内完成，达到本人/班级日额度或未结束任务上限时 429。失败任务 retry 重放返回同一后继，新的后继保留冻结依据、计新额度，一条链默认最多 3 次尝试。外部 retry_of 不接受，使用专用 retry 路径。

- GET `/student/resource-generation/usage`：学生本人。
- GET `/teacher/classes/:class_id/resource-generation/usage`：当前班级教师/管理员，学生 403、越权 404。
- 返回 scope=resource、audience、class_id、request_limit、requests_used、requests_remaining、active_tasks、active_limit、attempt_limit、UTC period_start/reset_at。
- ResourceTask 新增 retry_remaining；达到上限后 recoverable=false。队列提交失败仍返回已创建的 failed 任务编号，不能把已接纳误报为未提交。
- 默认资源本人 10/UTC 日、班级 60/UTC 日，排队+运行上限为本人 2、班级 6、全局 12。新字段 class_id/retry_root_id/request_body_hash 及索引由 20261018_0031 添加，旧值不回填。
- 反例出题新增班级最近 24 小时 20 次、班级未结束 4、全局未结束 8；保留原每教师日额/活跃数与重试上限。创建/重试共享跨进程接纳锁。

详见 [资源接纳与容量说明](docs/2026-10-18-resource-admission.md)。独立教师 RAG 的接纳额度见下节；这里的任务额度不代表 token 或货币余额。


## 2026-10-18 补充：独立教师/管理员 RAG 请求恢复

POST `/rag/query` 接受 UUID request_id。学生继续委托 TutorService；教师/管理员由数据库短锁接纳，同账号同编号同有效正文重放已完成结果，不再调用模型或占用额度。改正文/策略版本返回 409，其他账号请求返回 404，处理中返回 409/request_in_progress。失败或租约过期携带原编号和正文可重试，每次接纳计入当天额度，默认包含首次最多 3 次。

- GET `/rag/requests/:request_id`：仅本人教师/管理员，返回 request_id、status（processing/complete/failed/expired）、attempts_remaining、answer；未完成时 answer=null。GET 不触发模型，恢复完成结果仍复核当前身份和所有材料的访问范围、版本与正文摘要。
- GET `/rag/usage`：仅本人教师/管理员，返回 scope=rag、request_limit、requests_used、requests_remaining、active_requests、concurrency_limit、attempt_limit、UTC period_start/reset_at。
- 生成前后及恢复时复核来源；管理员调试的未入选候选也受保护。失效时 409/sources_changed，不返回缓存正文；教师仍可访问自己的资料，取消面向学生发布不等于撤销教师权限。
- 默认 40 次/UTC 日，个人有效处理租约 2、全局 8，租约 300 秒；失败重试计额度，完成重放和 GET 恢复不计。过期旧工作者不能覆盖新尝试，但已发送外部调用不能保证撤销。
- 专用错误 data.reason 区分 request_in_progress、request_conflict、sources_changed、access_changed、lease_expired、daily_limit、capacity_reached、attempt_limit、not_found、invalid_request；无缓存正文。普通参数错误保持原 400 形态。
- 迁移 20261018_0032 新增 rag_requests/rag_request_attempts，不回填旧问答；数据结构保留服务端私有结果，与只记元数据的模型账本分开。管理员恢复入口和本人额度面板沿用原主题变量。

说明、配置与验证：[独立 RAG 运行控制](docs/2026-10-18-rag-runtime-controls.md)。这些是问答尝试额度，不能当成 token 余额、货币预算或实测高并发能力。


## 2026-10-18 补充：模型公开价格估算

GET `/ai/usage` 和 GET `/teacher/classes/:class_id/ai-usage` 新增 `cost_estimate`，沿用原本人/班级权限、UTC 日范围与工作流过滤。

- status=no_calls/unpriced/partial/estimated；basis=published_rates_estimate，invoice_verified=false。
- estimated_calls/unpriced_calls；by_currency 各项含 currency、min/max（十进制字符串）、calls、range_calls；不同币种不合计、不换算。
- unpriced_reasons（原因→次数）、by_workflow（按工作流的已估算/未估算次数和币种金额）。历史 null 计 historical_unpriced；失败/中断、未知模型/渠道、价格过期、用量缺失或不一致都不视作免费。
- 原 cost=null 保留，表示没有核对过的实际实付金额；cost_status 扩展为 estimate_available/not_priced。estimated 状态可以是区间估算，不能当作账单确认。
- 数据迁移 20261018_0033 新增 cached_input_tokens、cost_status、cost_currency、cost_min/cost_max、price_snapshot，保留历史 null。价格在实际 HTTP 尝试开始时冻结，以响应模型匹配；不追溯补价。
- 仅已核实的标准纯文本调用可估算。每条价格带来源、版本/哈希、核对时间和有效期；自定义服务器 JSON 由 AI_MODEL_RATE_CARD_FILE 指定，不接受客户端价格。内置条目目前覆盖 DeepSeek Flash 与 OpenAI GPT-4o Mini 官方渠道，截止 2026-10-25T00:00:00Z 后须复核。

价格口径、操作和验证：[模型调用成本估算](docs/2026-10-18-model-cost-estimates.md)。费用是平台调用成本估算，不是向用户收费；不含税费、协议折扣、赠金和其他基础设施费用。


## 2026-10-18 补充：当前班级学习与辅导观察

GET `/teacher/classes/:class_id/learning-observations?days=14`：仅本班当前有效教师；匿名 401，非教师或越权 403。days 仅支持 7/14/30，否则 400；读取超过统计上限 422，不返回截断指标。

- `policy_version=classroom-observation-v1`，`scope=current_students_frozen_formal_class`；window 含 UTC start/as_of、days。当前有效学生人数与有纳入辅导请求的学生人数分别返回，不代表研究招募人数。
- `flow` 含 requests、states、published_help、display_confirmed、not_display_confirmed。请求按首次接纳时间计，重复重放不增加；可计数帮助、展示确认和请求完成不是相同口径。
- `formal_practice` 含 total、independent/independent_correct、assisted/assisted_correct。只接受正式服务端判题事件；independent 的准确含义为作答前平台内没有该题展示回执，不排除外部帮助。
- `followup` 按学生/知识点首次展示合并，七天内另一题的首次无平台提示正式判题计 observed，分 first_correct/first_incorrect；无记录分 window_open 与 window_closed_without_observation，都不算失败。
- `latency_ms` 分 completed_request、finished_attempt、finished_model_call、model_by_status，每项带 samples/missing/p50/p95；无有效样本为 null，方法 nearest_rank。unfinished_attempts/unfinished_model_calls 另外返回，不拿当前时间补结束耗时。不是首字或页面端到端性能指标。
- 迁移 20261018_0034 增加 TutorSession 可空 class_id/formal_question_id/concept_id 与班级时间索引；新正式判题事件冻结班级。旧记录不回填，转班不重新归属。
- 仅聚合当前本班学生发生时绑定本班的记录；不返回学生身份、题目文本、代码、提问、回答、请求或回执编号。GET 无模型调用、成绩或事件写入。

详见 [班级辅导与后续练习观察](docs/2026-10-18-classroom-observations.md)。展示、时间关联与判题不能直接作为有效帮助或学习提升的因果证明；成本、真实试用队列与人工教学评测仍另行验证。


## 2026-10-18 补充：分页学习证据

- GET `/student/learning-evidence`：本人当前有效学生；GET `/teacher/students/:student_id/learning-evidence`：当前任课教师读取本班学生历史，每次翻页重新鉴权。成功响应 no-store，不触发任何学习状态写入。
- limit 默认 20、最大 50；首次可传 snapshot_version 固定至已显示状态版本；后续 cursor 与 snapshot_version 互斥。禁止重复参数或非法数字。
- 返回 course、snapshot_version、latest_version、items、has_more、next_cursor、limit。按状态版本倒序，以游标边界查询；新事件不插入既有翻页，刷新后才切换版本。
- items 白名单：event_id/version/kind/reason/policy_version/concept_id/question_title/question_id/evidence_scope/occurred_at/processed_at。与原 learner-state.changes 共用序列化，后者新增每条 policy_version；不返回原 payload、changes、答案、隐藏测试或代码。
- 签名游标绑定账号/目标学生/角色/状态/版本和边界，有效期一小时；非法 400、越权 403、状态或版本冲突 409、过期 410。无历史时空 items，has_more=false；未处理事件仅由原状态摘要提示。
- 复用已有状态变更唯一索引，本轮无数据迁移。学生资料与教师档案增加“查看更早证据”，账号/学生切换及卸载失效迟到结果，审核成功后重新读取新版本。

详见 [学习证据历史分页](docs/2026-10-18-learning-evidence-history.md)。


## 2026-10-18 补充：受限 Python 逐行轨迹

- POST `/code/trace`：仅本人有效学生；输入 code、可选 stdin/language，以及既有 question_ref/formal_question_id/question_version。不接受客户端轨迹、run_id 或通过标记。
- 默认 `CODE_TRACE_ENABLED=false`，只支持现有 Docker 隔离适配器；配置声明在 GET `/code/languages` 的 `data.execution.trace`，不等同于运行健康检查。
- 成功返回 run_id/code_hash/question_version、trace_status、trace、graded=false、evidence_scope=self_test。trace 含执行前变量快照、停止时变量、输入输出、运行时异常/步数/输出上限、实际镜像 SHA 和代码/输入哈希；nonce 不返回。
- 12 KiB 代码、200 行、1,000 AST 节点、4 KiB 输入/输出、最多 80 步、每步至多 6 个有限长度变量。导入、函数定义、属性访问、推导式等不在本轮子集。
- 本人代码与题目版本绑定的 TutorCodeRun(kind=trace)，不创建正式成绩或学习事件；400 输入不合规，401/403 鉴权失败，409 上下文变化，503 配置关闭或隔离环境不可用。不支持宿主机回退。
- 小 E 的 algorithm_trace 可返回服务端附加 execution_trace，与模型的 trace_steps 分开；向模型仅发送最多 10 步节选，历史完整有限记录不变。

当前真实 Docker 轨迹验收未通过，保持开关关闭。详见 [Python 逐行执行轨迹](docs/2026-10-18-python-execution-traces.md)。

## 2026-10-19：学习证据驱动的反例推荐（兼容扩展）

现有学生辅导/聊天响应增加可选 `counterexample_pick`：`id`、`title`、`revision`、`version`（题目 manifest 摘要）、`concept_id`、`state_version`、`evidence_ids`、`reason`、`practice_path`。学习决策摘要另含 `misconception_kind`；推荐只消费服务端决策，不接受客户端自报误概念。

合规的“下一步提示”和下一题建议可返回该字段；无合适材料时为 null 或省略，旧客户端仍可读取原响应。当前仅匹配重复/已确认的循环边界证据，使用同一冻结状态，只选当前班级、当前已审发布且未成功完成的挑战。响应不含内部缺陷标签、修正程序、隐藏测试。概念限定任务不附带定向挑战。

历史读取与完成请求重放会重新核验推荐的权限、版本和完成状态；失效时返回 `counterexample_pick: null` 及 `recommendation_notice`，原回答保留，不追加模型调用。前端用固定站内路由与挑战 ID 生成链接，携带 `version` 查询参数；版本变化时阻止静默进入不同题目的作答区。详情/提交仍由现有服务执行最终校验。无新增 API 或数据库迁移，详见 [反例推荐说明](docs/2026-10-19-counterexample-recommendations.md)。

## 2026-10-22 学生端练习与资源回收站

新增正式作答、收藏、六题自主考试、七天回收站，以及关联提问 submission_id。接口与权限、迁移和验收口径见 [学生端体验与练习体系升级](docs/2026-10-22-student-experience-upgrade.md)。

## 2026-10-22 三端顶部与学生布局修正

新增 `GET /api/v1/student/trial-stats/records`，仅登录学生本人可读；支持 `status=all|completed|active`、`page`（默认 1）、`page_size`（默认 10，1–50）。返回 `items,total,page,page_size`，记录白名单为 `id,trial_id,title,status,score,joined_at,completed_at`，未完成成绩为 null。与原战绩汇总共用本人班级试炼可见性规则，排除内部沙箱，不包含自主考试或普通练习。不新增数据库表或迁移。

接口契约、完整统计口径及浏览器验收见 [三端顶部与学生端布局修正](docs/2026-10-22-ui-layout-refinement.md)。