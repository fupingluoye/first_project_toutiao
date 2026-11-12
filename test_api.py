# -*- coding: utf-8 -*-
"""
toutiao_backend 测试套件。

覆盖路由挂载、参数校验、JWT/鉴权工具、缓存键设计与资讯接口行为，
共 23 个用例。所有外部依赖（MySQL / Redis / RabbitMQ）均以 mock 替代，
唯一前提是项目根目录存在 .env（config.py 在导入时读取）。

运行方式：pytest test_api.py -v
运行依赖：pytest、httpx
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PROJ_ROOT = Path(__file__).resolve().parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

if not (PROJ_ROOT / ".env").exists():
    pytest.skip("需要项目根目录的 .env（config.py 导入即读）", allow_module_level=True)

import jwt

from cache import news_cache as cache_mod
from crud import news_cache as crud_news_cache
from fastapi.testclient import TestClient
from main import app
from utils import security
from utils.auth import AccessAuthToken, AuthToken

client = TestClient(app)

EXPECTED_PATHS = {
    "/",
    "/api/news/categories", "/api/news/list", "/api/news/detail",
    "/api/user/register", "/api/user/varify_email", "/api/user/login",
    "/api/user/refresh", "/api/user/info", "/api/user/update",
    "/api/user/password", "/api/user/logout", "/api/user/cancel",
    "/api/favorite/check", "/api/favorite/add", "/api/favorite/remove",
    "/api/favorite/list", "/api/favorite/clear",
    "/api/history/add", "/api/history/list",
    "/api/history/delete/{history_id}", "/api/history/clear",
}

REAL_PATHS = {
    r.path for r in app.routes
    if getattr(r, "methods", None)
    and not r.path.startswith(("/openapi", "/docs", "/redoc"))
}


def async_return(value):
    """把固定返回值包装为 async 函数，用于替换 crud 层的异步方法。"""

    async def _fake(*args, **kwargs):
        return value

    return _fake


class RecordingCC:
    """cache_conf 的替身：只记录 set_cache 调用参数，不连接 Redis。"""

    def __init__(self):
        self.calls = []

    async def set_cache(self, key, value, expire):
        self.calls.append((key, value, expire))
        return True


def _mock_list_items(n):
    return [
        {
            "id": i, "title": f"新闻{i}", "description": "简介", "image": "",
            "author": "编辑", "categoryId": 1, "views": 5,
            "publishedTime": "2026-01-01T00:00:00",
        }
        for i in range(1, n + 1)
    ]


class TestRouteRegistration:
    """验证 21 个业务接口与根路由全部挂载到 app。"""

    def test_all_expected_routes_registered(self):
        """所有预期路由都已注册，缺失时报出具体路径。"""
        missing = EXPECTED_PATHS - REAL_PATHS
        assert not missing, f"以下路由没挂上 app：{missing}"

    def test_route_count_is_21_plus_root(self):
        """路由总数守卫：接口增删时第一时间报警。"""
        assert len(REAL_PATHS) == len(EXPECTED_PATHS)


class TestParamValidation:
    """验证非法分页参数在进入数据库之前被 422 拦截。"""

    def test_list_without_category_id_is_422(self):
        """列表接口缺少必填参数 categoryId 返回 422。"""
        assert client.get("/api/news/list").status_code == 422

    def test_list_page_zero_is_422(self):
        """page 定义了 ge=1，传 0 返回 422。"""
        resp = client.get("/api/news/list", params={"categoryId": 1, "page": 0})
        assert resp.status_code == 422

    def test_list_page_size_over_100_is_422(self):
        """pageSize 定义了 le=100，传 101 返回 422。"""
        resp = client.get("/api/news/list", params={"categoryId": 1, "pageSize": 101})
        assert resp.status_code == 422

    def test_list_page_size_zero_is_422(self):
        """pageSize 定义了 ge=1，传 0 返回 422。"""
        resp = client.get("/api/news/list", params={"categoryId": 1, "pageSize": 0})
        assert resp.status_code == 422


class TestJwtUtils:
    """验证 utils/security.py 中 JWT 与密码工具的行为约定。"""

    def test_jwt_roundtrip_access_token(self):
        """签发的 access token 能解出 sub/role，且 refresh 标记为 False。"""
        payload = security.decode_token(security.create_token(42))
        assert payload["sub"] == "42"
        assert payload["role"] == "user"
        assert payload["refresh"] is False

    def test_jwt_refresh_token_flag_and_expiry(self):
        """refresh token 携带 refresh=True，有效期固定 7 天。"""
        payload = security.decode_token(security.create_token(42, refresh=True))
        assert payload["refresh"] is True
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        days = (exp - datetime.now(timezone.utc)).total_seconds() / 86400
        assert 6.9 < days < 7.1

    def test_jwt_expired_token_returns_none(self):
        """已过期 token 返回 None。"""
        token = security.create_token(1, expire_time=timedelta(seconds=-5))
        assert security.decode_token(token) is None

    def test_jwt_tampered_token_returns_false(self):
        """密钥不符的伪造 token 返回 False（与过期的 None 区分开）。"""
        fake = jwt.encode(
            {"sub": "1", "role": "user", "refresh": False,
             "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            "wrong-secret", algorithm="HS256",
        )
        assert security.decode_token(fake) is False

    def test_generate_code_is_six_digits(self):
        """验证码是 100000-999999 范围内的 6 位数字字符串。"""
        code = security.generate_code()
        assert len(code) == 6 and code.isdigit()

    def test_password_hash_and_verify(self):
        """bcrypt 哈希不可逆，且正确密码校验通过、错误密码失败。"""
        hashed = security.get_hash_password("S3cret!pw")
        assert hashed != "S3cret!pw"
        assert security.verify_password("S3cret!pw", hashed) is True
        assert security.verify_password("wrong", hashed) is False


class TestAuthLogic:
    """验证 AccessAuthToken 的角色与令牌类型校验规则。"""

    def test_access_token_passes_role_check(self):
        """普通用户 access token 通过角色校验。"""
        payload = security.decode_token(security.create_token(1))
        assert AccessAuthToken().verify_token_data(payload) is True

    def test_refresh_token_fails_role_check(self):
        """refresh token 不允许当作 access token 使用。"""
        payload = security.decode_token(security.create_token(1, refresh=True))
        assert AccessAuthToken().verify_token_data(payload) is False

    def test_admin_role_fails_user_check(self):
        """非 user 角色（如 admin）不通过校验。"""
        payload = security.decode_token(security.create_token(1, role="admin"))
        assert AccessAuthToken().verify_token_data(payload) is False

    def test_base_authtoken_verify_token(self):
        """基类只判断 token 是否存在：有效 dict 为 True，None/False 为 False。"""
        assert AuthToken().verify_token({"sub": "1"}) is True
        assert AuthToken().verify_token(None) is False
        assert AuthToken().verify_token(False) is False


class TestCacheKeys:
    """验证 cache/news_cache.py 的缓存键拼装与穿透防护 TTL。"""

    def test_news_list_cache_key_format(self, monkeypatch):
        """列表缓存键格式为 news_list{categoryId}:{page}:{pageSize}，默认 TTL 7200。"""
        fake = RecordingCC()
        monkeypatch.setattr(cache_mod, "cc", fake)
        asyncio.run(cache_mod.set_cache_news_list(3, 2, 10, []))
        assert fake.calls[0][0] == "news_list3:2:10"
        assert fake.calls[0][2] == cache_mod.EXPIRE_TIME

    def test_news_list_cache_key_all_when_category_none(self, monkeypatch):
        """categoryId 为 None 时键中的分类段写作 all。"""
        fake = RecordingCC()
        monkeypatch.setattr(cache_mod, "cc", fake)
        asyncio.run(cache_mod.set_cache_news_list(None, 1, 10, []))
        assert fake.calls[0][0] == "news_listall:1:10"

    def test_missing_news_detail_cached_with_short_ttl(self, monkeypatch):
        """缓存穿透防护：不存在的新闻写入占位缓存，TTL 缩短为 600 秒。"""
        fake = RecordingCC()
        monkeypatch.setattr(cache_mod, "cc", fake)
        asyncio.run(cache_mod.set_cache_news_detail(999, {"error": "数据不存在，请检查新闻id是否正确"}))
        key, _, expire = fake.calls[0]
        assert key == "news:details:999"
        assert expire == cache_mod.NOT_DETAIL_EXPIRE_TIME == 600


class TestNewsApi:
    """mock crud 层，验证资讯接口自身的编排逻辑与响应契约。"""

    def test_list_cache_hit_and_redis_views_override(self, monkeypatch):
        """列表接口：命中缓存不再触库；Redis 有浏览量则覆盖，无则保留缓存旧值。"""
        monkeypatch.setattr(crud_news_cache, "get_news_list", async_return(_mock_list_items(2)))
        monkeypatch.setattr(crud_news_cache, "get_many_news_views", async_return([7, None]))
        monkeypatch.setattr(crud_news_cache, "get_news_count", async_return(2))

        resp = client.get("/api/news/list", params={"categoryId": 1, "page": 1, "pageSize": 10})
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert body["code"] == 200
        assert data["total"] == 2
        assert data["hasMore"] is False
        assert data["list"][0]["views"] == 7
        assert data["list"][1]["views"] == 5
        assert "categoryId" in data["list"][0]

    def test_list_has_more_true(self, monkeypatch):
        """10 条/页、总量 25 条时第一页 hasMore 为 True。"""
        monkeypatch.setattr(crud_news_cache, "get_news_list", async_return(_mock_list_items(10)))
        monkeypatch.setattr(crud_news_cache, "get_many_news_views", async_return([None] * 10))
        monkeypatch.setattr(crud_news_cache, "get_news_count", async_return(25))

        resp = client.get("/api/news/list", params={"categoryId": 1, "page": 1, "pageSize": 10})
        assert resp.json()["data"]["hasMore"] is True

    def test_detail_404_with_envelope(self, monkeypatch):
        """查询不存在的新闻返回 404，且套用统一响应信封。"""
        monkeypatch.setattr(
            crud_news_cache, "get_news_detail",
            async_return({"error": "数据不存在，请检查新闻id是否正确"}),
        )
        resp = client.get("/api/news/detail", params={"id": 999})
        assert resp.status_code == 404
        body = resp.json()
        assert body["code"] == 404
        assert body["message"] == "新闻不存在"
        assert body["data"] is None

    def test_detail_success(self, monkeypatch):
        """详情接口成功路径：views 以 Redis 累计值为准，附带 relatedNews，字段保持 camelCase。"""
        detail = {
            "id": 1, "title": "新闻1", "description": "简介", "image": "",
            "author": "编辑", "categoryId": 1, "views": 5,
            "publishedTime": "2026-01-01T00:00:00", "content": "正文",
        }
        monkeypatch.setattr(crud_news_cache, "get_news_detail", async_return(detail))
        monkeypatch.setattr(crud_news_cache, "increase_news_views", async_return(9))
        monkeypatch.setattr(crud_news_cache, "get_related_news", async_return([]))
        monkeypatch.setattr(crud_news_cache, "get_many_news_views", async_return([]))

        resp = client.get("/api/news/detail", params={"id": 1})
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert body["code"] == 200
        assert data["views"] == 9
        assert data["content"] == "正文"
        assert data["relatedNews"] == []
        assert "publishedTime" in data and "categoryId" in data
