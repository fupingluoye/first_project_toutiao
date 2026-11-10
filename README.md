# 资讯类 App 后端服务

基于 **FastAPI + SQLAlchemy 2.0 异步 ORM** 构建的资讯类移动应用后端，提供用户认证、资讯分类/列表/详情、收藏、浏览历史等能力，并使用 **Redis** 缓存热点数据。

全链路 `async/await`：路由层 → 数据访问层 → `aiomysql` → `redis.asyncio`，无同步阻塞调用。

## 功能特性

- **用户模块**：注册、登录、获取/修改个人信息、修改密码
- **认证**：签发 `Bearer` Token（存于 `user_token` 表，7 天有效期），依赖注入解析当前用户
- **资讯模块**：分类列表、按分类分页浏览、详情查看（浏览量自增 + 同类推荐）
- **收藏模块**：收藏 / 取消收藏 / 收藏状态查询 / 分页列表 / 清空，`user_id + news_id` 唯一约束保证幂等
- **历史模块**：记录浏览（同一新闻重复浏览只更新时间）、分页列表、删除单条、清空
- **缓存**：Redis 缓存分类列表与资讯分页列表，未命中自动回源并回填
- **统一响应**：全站 `{code, message, data}` 信封
- **全局异常处理**：业务异常 / 数据库完整性约束 / 数据库异常 / 兜底异常四级拦截

## 技术栈

| 类别 | 选型 |
|---|---|
| Web 框架 | FastAPI |
| ASGI 服务器 | Uvicorn |
| ORM | SQLAlchemy 2.0（`Mapped` / `mapped_column` 声明式风格，全异步） |
| 数据库 | MySQL 8.x（驱动 `aiomysql`） |
| 缓存 | Redis（客户端 `redis.asyncio`） |
| 数据校验 | Pydantic v2（`Field(alias=)` 适配前端驼峰命名） |
| 密码哈希 | passlib + bcrypt |
| Python | 3.12 |

## 项目结构

```
toutiao_backend/
├── main.py                 # 应用入口：注册全局异常、CORS 中间件、挂载路由
├── alembic.ini             # Alembic 配置
├── myalembic/              # 迁移脚本目录（versions/ 必须随仓库提交）
├── configs/
│   ├── db_config.py        # 异步数据库引擎、会话工厂、get_db 依赖
│   └── cache_conf.py       # Redis 客户端与缓存读写封装（含 JSON 序列化）
├── celerys/                # Celery 异步任务（邮件验证码）
├── models/                 # ORM 模型
│   ├── news.py             # 新闻分类、新闻
│   ├── users.py            # 用户、用户令牌
│   ├── favorite.py         # 收藏
│   └── history.py          # 浏览历史
├── schemas/                # Pydantic 请求 / 响应模型
├── crud/                   # 数据访问层
│   ├── users.py            # 用户、令牌、鉴权
│   ├── news_cache.py       # 资讯查询（带缓存回源逻辑）
│   ├── favorite.py         # 收藏
│   └── history.py          # 浏览历史
├── routers/                # 路由层
│   ├── users.py            # /api/user
│   ├── news.py             # /api/news
│   ├── favorite.py         # /api/favorite
│   └── history.py          # /api/history
├── cache/
│   └── news_cache.py       # 缓存键设计与读写封装
└── utils/
    ├── auth.py             # 当前用户依赖（解析 Bearer Token）
    ├── security.py         # 密码哈希与校验
    ├── response.py         # 统一成功响应
    ├── exception.py        # 异常处理器实现
    └── exception_handlers.py  # 异常处理器注册
```

分层约定：`routers → crud → models`；`schemas` 作为接口契约，`utils` 提供横切能力。

## 快速开始

### 1. 环境要求

- Python 3.12+
- MySQL 8.x
- Redis 5.x 及以上

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install fastapi "uvicorn[standard]" sqlalchemy aiomysql redis alembic celery \
            pydantic pydantic-settings python-dotenv \
            "passlib[bcrypt]" "bcrypt>=4.0,<5"
```

> 注意：`sqlalchemy` 异步模式需要 `greenlet`，通常随 SQLAlchemy 一起装上；若报缺失请显式安装。
> `bcrypt` 请锁定 `<5`：5.x 移除了 72 字节自动截断，会与 passlib 冲突。

### 3. 配置环境

复制 `.env.example` 为 `.env`，填入你的真实值：

```bash
cp .env.example .env
```

所有连接串与口令（MySQL / Redis / Celery / SMTP / JWT 密钥）都从 `.env` 读取（`pydantic-settings`），代码与仓库中不含任何明文凭据。注意两个细节：

- 密码含 `@` 等特殊字符时，在 `DATABASE_URL` / `BROKER` / `BACKEND` 里要 URL 编码（`@` → `%40`）；Redis 客户端的 `REDIS_PASSWORD` 写原值即可。
- Redis 客户端已显式指定 `protocol=2`，以兼容 Redis 5.x（6.0 之前不支持 RESP3 握手）。

### 4. 初始化数据表

表结构由 Alembic 管理：

```bash
# 生成迁移脚本（模型与库有差异时）
alembic revision --autogenerate -m "your message"

# 执行迁移建表
alembic upgrade head

# 校验模型与库是否一致
alembic check
```

同时需准备基础数据：至少插入若干条 `news_category` 与 `news` 记录。

### 5. 启动服务

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问：

- 交互式接口文档（Swagger UI）：<http://127.0.0.1:8000/docs>
- OpenAPI 描述文件：<http://127.0.0.1:8000/openapi.json>

## 环境变量

全部配置集中在项目根目录 `.env`（键清单见 `.env.example`）：`DATABASE_URL`、`REDIS_HOST/PORT/DB/PASSWORD`、`JWT_SECRET_KEY`、`BROKER`、`BACKEND`、`SMTP_*`。

`.env` **已加入 `.gitignore`，不会提交**；仓库内只提交 `.env.example` 作为模板。

## 接口说明

- 统一前缀：`/api`
- 需要登录的接口通过请求头传递令牌：

```
Authorization: Bearer <token>
```

### 接口清单

| 模块 | 方法 | 路径 | 说明 | 需要登录 |
|---|---|---|---|---|
| 资讯 | GET | `/api/news/categories` | 获取新闻分类 | 否 |
| 资讯 | GET | `/api/news/list` | 按分类分页获取新闻 | 否 |
| 资讯 | GET | `/api/news/detail` | 新闻详情（浏览量 +1，含同类推荐） | 否 |
| 用户 | POST | `/api/user/register` | 注册（返回 token 与用户信息） | 否 |
| 用户 | POST | `/api/user/login` | 登录 | 否 |
| 用户 | GET | `/api/user/info` | 获取当前用户信息 | 是 |
| 用户 | PUT | `/api/user/update` | 修改昵称/头像/性别/简介/手机号 | 是 |
| 用户 | PUT | `/api/user/password` | 修改密码（校验旧密码） | 是 |
| 收藏 | GET | `/api/favorite/check` | 查询某新闻是否已收藏 | 是 |
| 收藏 | POST | `/api/favorite/add` | 添加收藏 | 是 |
| 收藏 | DELETE | `/api/favorite/remove` | 取消收藏 | 是 |
| 收藏 | GET | `/api/favorite/list` | 收藏分页列表 | 是 |
| 收藏 | DELETE | `/api/favorite/clear` | 清空收藏 | 是 |
| 历史 | POST | `/api/history/add` | 添加浏览记录 | 是 |
| 历史 | GET | `/api/history/list` | 浏览历史分页列表 | 是 |
| 历史 | DELETE | `/api/history/delete/{history_id}` | 删除单条浏览记录 | 是 |
| 历史 | DELETE | `/api/history/clear` | 清空浏览历史 | 是 |
| 根 | GET | `/` | 健康检查 | 否 |

### 主要请求参数

| 接口 | 参数 | 位置 | 类型 | 默认值 | 备注 |
|---|---|---|---|---|---|
| `/api/news/categories` | `skip` / `limit` | Query | int | 0 / 100 | 分页 |
| `/api/news/list` | `categoryId` | Query | int | 必填 | 分类 ID |
| | `page` / `pageSize` | Query | int | 1 / 10 | `pageSize` 上限 100 |
| `/api/news/detail` | `id` | Query | int | 必填 | 新闻 ID |
| `/api/user/register`、`/login` | `username` / `password` | Body | str | — | 长度 3–50 / 6–100 |
| `/api/user/update` | `nickname`、`avatar`、`gender`、`bio`、`phone` | Body | str | 均可选 | 仅更新传入字段 |
| `/api/user/password` | `oldPassword` / `newPassword` | Body | str | 必填 | `newPassword` 至少 6 位 |
| `/api/favorite/check`、`/remove` | `newsId` | Query | int | 必填 | 新闻 ID |
| `/api/favorite/add`、`/api/history/add` | `newsId` | Body | int | 必填 | 新闻 ID |
| `/api/favorite/list`、`/api/history/list` | `page` / `pageSize` | Query | int | 1 / 10 | 分页 |

列表类接口统一返回：

```json
{
  "code": 200,
  "message": "获取列表成功",
  "data": {
    "list": [],
    "total": 0,
    "hasMore": false
  }
}
```

### 响应格式

成功响应统一为：

```json
{ "code": 200, "message": "success", "data": null }
```

异常响应保持同样的信封结构，`code` 与 HTTP 状态码一致：

| 场景 | HTTP | 说明 |
|---|---|---|
| 业务异常 | 400 / 401 / 404 | 由路由主动抛出 `HTTPException` |
| 数据完整性约束冲突 | 400 | 如用户名已存在、关联数据不存在、中断约束 |
| 数据库异常 | 500 | 返回统一的数据库失败提示 |
| 未捕获异常 | 500 | 由兜底处理器接管 |

> 当前 Pydantic 参数校验失败仍返回 FastAPI 默认的 `{"detail": [...]}`，未套用上述信封，见「待办」。

## 数据库设计

共 6 张表：

| 表名 | 说明 | 关键约束 / 索引 |
|---|---|---|
| `news_category` | 新闻分类 | `name` 唯一 |
| `news` | 新闻 | 索引 `fk_news_category_idx(category_id)`、`idx_publish_time(publish_time)` |
| `user` | 用户 | `username`、`phone` 唯一 |
| `user_token` | 登录令牌 | `token` 唯一；索引 `fk_user_token_user_idx(user_id)` |
| `favorite` | 收藏 | 唯一约束 `user_news_unique(user_id, news_id)`；`user_id`、`news_id` 索引 |
| `history` | 浏览历史 | 索引 `fk_history_user_idx(user_id)`、`fk_history_news_idx(news_id)`、`idx_view_time(view_time)` |

`favorite` 的唯一约束由数据库层面保证「同一用户对同一新闻只能收藏一次」，避免并发下的重复插入。

## 缓存设计

| 用途 | Key 格式 | TTL |
|---|---|---|
| 新闻分类 | `news:categoties` | 7200 s |
| 新闻分页列表 | `news_list:{categoryId}:{page}:{pageSize}` | 1800 s |

- 缓存读取失败时自动降级查库，不影响接口可用性。
- 分类数据整体缓存；资讯列表按「分类 + 页码 + 每页条数」维度缓存。
- 缓存对象统一以 JSON 形式存储（`ensure_ascii=False` 保留中文）。
- Key 的拼装集中在 `cache/news_cache.py`，便于统一维护。

## 待办

- [ ] 补充 pytest + httpx 接口测试
- [ ] 统一 `RequestValidationError` 的响应信封
- [ ] 提供 Dockerfile 与 docker-compose（应用 + MySQL + Redis 一键启动）
- [ ] 为列表接口补充压测数据与缓存命中率统计
- [ ] 令牌续期与改密后吊销全部会话

## 说明

本项目为个人学习项目，用于实践 FastAPI 异步后端的分层设计与缓存、鉴权等常见能力。
