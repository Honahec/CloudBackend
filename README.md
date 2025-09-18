# CloudBackend

## JWT 认证说明

本系统使用 JWT (JSON Web Token) 进行身份认证，提供安全且无状态的 API 访问方式。

### Token 配置

- **Access Token 有效期**: 60 分钟
- **Refresh Token 有效期**: 7 天
- **Token 轮换**: 启用（刷新时生成新的 refresh token）
- **黑名单支持**: 启用（注销时将 token 加入黑名单）

### 认证流程

1. 用户登录获取 access_token 和 refresh_token
2. 使用 access_token 访问受保护的 API
3. 当 access_token 过期时，使用 refresh_token 获取新的 token
4. 注销时将 refresh_token 加入黑名单

### Token 使用方式

在需要认证的 API 请求中，在请求头中包含：

```
Authorization: Bearer <access_token>
```

**重要提示:**

- 用户注册接口 (`POST /user/register/`) 不需要认证
- 用户登录接口 (`POST /user/login/`) 不需要认证
- Token 刷新接口 (`POST /user/refresh-token/`) 不需要认证，但需要有效的 refresh token
- 其他所有接口都需要有效的 JWT 认证

## API 文档

### 1. 用户注册

**接口:** `POST /user/register/`

**请求体:**

```json
{
  "username": "用户名",
  "email": "邮箱地址",
  "password": "密码",
  "display_name": "显示名称"
}
```

**注意:** `display_name` 字段是可选的，如果不提供则默认使用用户名。

**响应示例:**

```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "display_name": "testuser",
  "is_active": true,
  "permission": "user"
}
```

**错误响应:**

用户名已存在:

```json
{
  "error": "用户名已存在"
}
```

邮箱已存在:

```json
{
  "error": "邮箱已存在"
}
```

### 2. 用户登录 (JWT)

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
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "display_name": "testuser",
    "is_active": true,
    "permission": "user"
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**错误响应:**

```json
{
  "detail": "用户名或密码错误"
}
```

### 3. Token 刷新

**接口:** `POST /user/refresh-token/`

**请求体:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**响应示例:**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 4. 用户注销

**接口:** `POST /user/logout/`

**请求头:**

```
Authorization: Bearer <access_token>
```

**请求体:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**响应示例:**

```json
{
  "status": "登出成功"
}
```

### 5. 获取用户个人资料

**接口:** `GET /user/profile/`

**请求头:**

```
Authorization: Bearer <access_token>
```

**响应示例:**

```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "display_name": "testuser",
  "is_active": true,
  "permission": "user"
}
```

## 用户设置接口

### 6. 修改密码

**接口:** `POST /user/change-password/`

**请求头:**

```
Authorization: Bearer <access_token>
```

**请求体:**

```json
{
  "old_password": "旧密码",
  "new_password": "新密码"
}
```

**响应示例:**

```json
{
  "status": "密码更新成功"
}
```

**错误响应:**

```json
{
  "error": "旧密码错误"
}
```

### 7. 更新昵称

**接口:** `POST /user/update-display-name/`

**请求头:**

```
Authorization: Bearer <access_token>
```

**请求体:**

```json
{
  "display_name": "新的昵称"
}
```

**响应示例:**

```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "display_name": "新的昵称",
  "is_active": true,
  "permission": "user"
}
```

### 8. 更新邮箱

**接口:** `POST /user/update-email/`

**请求头:**

```
Authorization: Bearer <access_token>
```

**请求体:**

```json
{
  "email": "newemail@example.com"
}
```

**响应示例:**

```json
{
  "id": 1,
  "username": "testuser",
  "email": "newemail@example.com",
  "display_name": "testuser",
  "is_active": true,
  "permission": "user"
}
```

**错误响应:**

```json
{
  "error": "邮箱已存在"
}
```

## 安全建议

1. **Token 存储**: 在生产环境中，建议将 token 存储在 HttpOnly Cookie 中而不是 localStorage
2. **HTTPS**: 生产环境必须使用 HTTPS 来保护 token 传输
3. **Token 轮换**: 系统已启用 token 轮换，每次刷新都会生成新的 refresh token
4. **短期有效**: Access token 有效期较短（60 分钟），降低安全风险
5. **黑名单**: 注销时 token 会被加入黑名单，防止重复使用

## 项目结构

```
CloudBackend/
├── manage.py                 # Django管理脚本
├── requirements.txt          # 项目依赖
├── CloudBackend/            # 主项目配置
│   ├── settings.py          # Django设置(包含JWT配置)
│   ├── urls.py              # URL路由配置
│   └── ...
└── cloud_auth/              # 认证应用
    ├── models.py            # 用户数据模型
    ├── views.py             # JWT认证视图
    ├── serializers.py       # 序列化器
    └── ...
```

## 异步文件上传到阿里云 OSS 功能说明

### 环境配置

#### 1. 环境变量配置

复制 `.env_example` 为 `.env` 并配置以下变量：

```env
# 阿里云OSS配置
ALIYUN_ACCESS_KEY=<your_access_key>
ALIYUN_ACCESS_KEY_SECRET=<your_access_secret>
OSS_ENDPOINT=<your_oss_endpoint>
OSS_BUCKET_NAME=<your_bucket_name>

# Celery配置 (Redis)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

#### 2. 启动 Redis 服务

确保 Redis 服务已启动（默认端口 6379）

#### 3. 启动 Celery Worker

```bash
celery -A CloudBackend worker --loglevel=info
```

#### 4. 启动 Django 服务

```bash
python manage.py runserver
```

### API 使用说明

#### 文件上传

**POST** `/file/`

请求体：

```json
{
  "name": "example.jpg",
  "content_type": "image/jpeg",
  "size": 1024000,
  "file_content": "base64_encoded_file_content_here"
}
```

响应：

```json
{
  "id": 1,
  "name": "example.jpg",
  "content_type": "image/jpeg",
  "size": 1024000,
  "upload_status": "pending"
}
```

#### 批量文件上传

**POST** `/file/`

请求体：

```json
[
  {
    "name": "file1.jpg",
    "content_type": "image/jpeg",
    "size": 1024000,
    "file_content": "base64_content_1"
  },
  {
    "name": "file2.pdf",
    "content_type": "application/pdf",
    "size": 2048000,
    "file_content": "base64_content_2"
  }
]
```

#### 查询上传状态

**GET** `/file/upload_status/?file_ids=1,2,3`

响应：

```json
[
  {
    "id": 1,
    "name": "example.jpg",
    "upload_status": "completed",
    "upload_error": null,
    "oss_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/files/1/xxx.jpg",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:05:00Z"
  }
]
```

#### 重新上传文件

**POST** `/file/{id}/retry_upload/`

请求体：

```json
{
  "file_content": "base64_encoded_file_content_here"
}
```

#### 文件列表

**GET** `/file/`

响应：

```json
[
  {
    "id": 1,
    "name": "example.jpg",
    "content_type": "image/jpeg",
    "size": 1024000,
    "oss_key": "files/1/xxx.jpg",
    "oss_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/files/1/xxx.jpg",
    "upload_status": "completed",
    "upload_error": null,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:05:00Z"
  }
]
```

### 上传状态说明

- `pending`: 待上传 - 文件记录已创建，等待异步任务处理
- `uploading`: 上传中 - 异步任务正在处理文件上传
- `completed`: 上传完成 - 文件已成功上传到 OSS
- `failed`: 上传失败 - 上传过程中出现错误

### 文件存储结构

OSS 中的文件按以下结构存储：

```
files/
  ├── {user_id}/
  │   ├── {uuid1}.jpg
  │   ├── {uuid2}.pdf
  │   └── ...
```
