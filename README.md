# CloudBackend

## API

### 1. 用户注册

**接口:** `POST /user/`

**请求体:**

```json
{
  "username": "用户名",
  "email": "邮箱地址",
  "password": "密码"
}
```

**响应示例:**

```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "is_active": true,
  "permission": "user"
}
```

**cURL 示例:**

```bash
curl -X POST http://127.0.0.1:8000/user/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

### 2. 用户登录

**接口:** `POST /user/login/`

**请求体:**

```json
{
  "username": "用户名",
  "password": "密码"
}
```

**响应示例:**

```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "is_active": true,
  "permission": "user"
}
```

### 3. 获取用户个人资料

**接口:** `GET /user/profile/`

**请求头:**

```
Authorization: Bearer <your_token>
```

**响应示例:**

```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "is_active": true,
  "permission": "user"
}
```

### 4. 获取所有用户列表

**接口:** `GET /user/`

**请求头:**

```
Authorization: Bearer <your_token>
```

**响应示例:**

```json
[
  {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "is_active": true,
    "permission": "user"
  }
]
```

### 5. 获取特定用户信息

**接口:** `GET /user/{id}/`

**请求头:**

```
Authorization: Bearer <your_token>
```

### 6. 更新用户信息

**接口:** `PUT /user/{id}/` 或 `PATCH /user/{id}/`

**请求头:**

```
Authorization: Bearer <your_token>
```

**请求体(PUT - 完整更新):**

```json
{
  "username": "newusername",
  "email": "newemail@example.com"
}
```

**请求体(PATCH - 部分更新):**

```json
{
  "email": "newemail@example.com"
}
```

### 7. 删除用户

**接口:** `DELETE /user/{id}/`

**请求头:**

```
Authorization: Bearer <your_token>
```

## 错误响应

当请求出错时，API 会返回相应的 HTTP 状态码和错误信息：

### 400 Bad Request

```json
{
  "error": "用户名已存在"
}
```

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden

```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found

```json
{
  "detail": "Not found."
}
```

## 认证说明

本 API 使用 Django REST Framework 的默认认证机制。在大多数需要认证的接口中，需要在请求头中包含有效的认证信息。

**注意:** 当前的认证实现可能需要配置具体的认证后端(如 Token 认证、Session 认证等)。请根据实际需求配置相应的认证方式。

## 项目结构

```
CloudBackend/
├── manage.py                 # Django管理脚本
├── requirements.txt          # 项目依赖
├── db.sqlite3               # SQLite数据库文件
├── CloudBackend/            # 主项目配置
│   ├── settings.py          # Django设置
│   ├── urls.py              # URL路由配置
│   └── ...
└── cloud_auth/              # 认证应用
    ├── models.py            # 数据模型
    ├── views.py             # 视图处理
    ├── serializers.py       # 序列化器
    └── ...
```

## 开发说明

- 数据库: SQLite (默认)
- 认证模型: 自定义 User 模型继承自 AbstractUser
- API 架构: RESTful API
- 跨域: 已配置 CORS 支持
