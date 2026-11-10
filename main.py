import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import favorite, history, news, users
from utils.exception_handlers import register_exception_handlers


async def _flush_news_views_loop(interval: int = 60):
    # 每 60 秒把 Redis 里累计的浏览量批量落库一次，随 lifespan 一起启停
    from configs.db_config import AsyncSessionLocal
    from crud.news_cache import flush_news_views_to_db

    while True:
        await asyncio.sleep(interval)
        try:
            async with AsyncSessionLocal() as db:
                await flush_news_views_to_db(db)
        except Exception as e:
            print(f"浏览量落库失败：{e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_flush_news_views_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)  # 注册全局异常处理


@app.get("/")
async def root():
    return {"msg": "hello world"}


# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许访问的源，全部，测试用可以，实际生产需要指定源
    allow_credentials=True,  # 允许携带cookie
    allow_methods=["*"],  # 允许所有的请求方法
    allow_headers=["*"],  # 允许所有请求头
)

# 挂载路由，挂routers文件夹下面news.py的路由
app.include_router(news.router)
app.include_router(users.router)
app.include_router(favorite.router)
app.include_router(history.router)