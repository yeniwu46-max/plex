---
name: Flask API 形态与鉴权
description: 审查 Flask 路由是否保持 /api/v1 前缀、统一 JSON 响应形态，以及 JWT/权限装饰器是否在应保护的新端点上正确使用。
---

# Flask API 形态与鉴权

## Context

后端在 `backend/app/`，蓝图普遍使用 **`url_prefix='/api/v1/...'`**（见 `backend/app/routes/auth.py` 等）。统一响应由 [backend/app/utils/response.py](backend/app/utils/response.py) 的 `success_response` / `error_response` / `paginated_response` 提供；鉴权与校验见 [backend/app/utils/decorators.py](backend/app/utils/decorators.py)（`role_required`、`permission_required`、`validate_request_json`）及 `flask_jwt_extended`。Linter 通常不会验证「新路由是否漏挂 JWT」或「响应是否与既有端点形态一致」。

## What to Check

### 1. URL 前缀与注册

- 新增 `Blueprint` 时：`url_prefix` 是否以 **`/api/v1`** 为根（与 [AGENTS.md](AGENTS.md)、[backend_api_design.md](backend_api_design.md) 一致）。
- 是否在 [backend/app/routes/__init__.py](backend/app/routes/__init__.py) 中 **`register_blueprint`**，避免「写了蓝图从未挂载」。
- **GOOD**：`Blueprint('users', __name__, url_prefix='/api/v1/users')` 并在 `register_routes` 注册。
- **BAD**：新 REST 挂在 `/` 或无版本前缀，与现有客户端约定冲突。

### 2. 响应函数用法一致性

- 对照 `success_response` / `error_response` 的**参数顺序与语义**（`message`、`code`、`data`、`status_code`）。禁止混用「把数字错误码当第一个位置参数当 message」等与 [response.py](backend/app/utils/response.py) 签名不一致的调用（易静默产生错误 JSON）。
- **GOOD**：`error_response("用户名或密码不能为空", 40001, None, 400)` 或与关键字参数一致。
- **BAD**：`error_response(40001, "某消息")` 等与签名语义颠倒、导致错误码与文案错位。

### 3. 鉴权与公开端点

- 对 **变更或新增** 的路由：判断业务上是否应登录或应限制角色/权限。
- 应保护的操作是否具备 **`@jwt_required()`**、`@role_required(...)`、`@permission_required(...)`** 之一**（或与项目既有模式等价的中间层）；注册/登录等公开端点除外。
- **GOOD**：删除用户、改权限、管理班级等敏感写操作带装饰器链。
- **BAD**：新增「写数据」或「读敏感数据」路由却完全无 JWT/权限校验且无注释说明为刻意公开。

## Key Files

- `backend/app/routes/**/*.py`
- `backend/app/routes/__init__.py`
- `backend/app/utils/response.py`
- `backend/app/utils/decorators.py`
- `backend/app/middleware/auth.py`（若存在与 JWT 相关的集中逻辑）

## Exclusions

- 仅修改 `models/`、`services/` 且未触及路由签名或 URL 的纯重构。
- 测试夹具或 `init_db.py` 等非 HTTP 入口文件。
