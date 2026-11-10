from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio.session import AsyncSession
from schemas.base import NewsDetail
from utils.response import success_response
from configs.db_config import get_db
from crud import  news_cache
from fastapi.encoders import jsonable_encoder
# 创建apirputer实例,prefix是路由前缀，tags是分组，方便在docs中查看一个分组中的接口

router = APIRouter(prefix="/api/news", tags=["news"])


# 路由,写完后在main.py中挂载，用app.include_router(news.router)
@router.get("/categories")
async def get_categories(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    # 读取新闻分类
    categories = await news_cache.get_categories(db, skip, limit)
    return success_response(data=categories)

# 获取新闻列表
@router.get("/list")
async def get_news_list(
    category_id: int = Query(..., alias="categoryId"),
    page: int = Query(1,ge=1),
    page_size: int = Query(10, alias="pageSize",ge =1, le=100),
    db: AsyncSession = Depends(get_db),
):

    offset = (page - 1) * page_size
    news_list = await news_cache.get_news_list(db, category_id, offset, page_size)
    news_list = jsonable_encoder(news_list)
    # 用 Redis 里的累计浏览量覆盖列表缓存中的旧值，保证每次返回都是最新
    scores = await news_cache.get_many_news_views([item["id"] for item in news_list])
    for item, score in zip(news_list, scores):
        if score is not None:
            item["views"] = score
    total = await news_cache.get_news_count(db, category_id)
    # 是否还有更多，当前的数量+列表里的数量<总量
    has_more = offset + len(news_list) < total
    datas = {"list": news_list, "total": total, "hasMore": has_more}
    return success_response(data=datas)
# 获取新闻详情
@router.get("/detail")
async def get_news_detail(
    news_id: int = Query(..., alias="id"), db: AsyncSession = Depends(get_db)
):
    # 获取新闻详情+浏览量+1  + 相关新闻
    # 根据新闻id查找数据，并相应更新浏览量
    news_detail = await news_cache.get_news_detail(db, news_id)
    if "error" in news_detail:
        raise HTTPException(status_code=404, detail="新闻不存在")
    # 浏览量入库
    views = await news_cache.increase_news_views(db, news_id)
    news_detail["views"] = views if views  else news_detail["views"]
    # 获取相关新闻
    related_news = await news_cache.get_related_news(
        db, news_detail['categoryId'], news_detail['id'], limit=4
    )
    # 相关新闻的浏览量同样以 Redis 为准
    scores = await news_cache.get_many_news_views([item["id"] for item in related_news])
    for item, score in zip(related_news, scores):
        if score is not None:
            item["views"] = score
    # data 里的 key 全部 camelCase，与收藏/历史/用户接口同一套命名
    data = NewsDetail(**news_detail)
    data["relatedNews"] = jsonable_encoder(related_news)
    return success_response(data=data)
    # return {
    #     "code": 200,
    #     "message": "获取详情成功",
    #     "data": {
    #         "id": news_detail['id']    ,
    #         "title": news_detail['title'],
    #         "content": news_detail['content'],
    #         "image": news_detail['image'],
    #         "author": news_detail['author'],
    #         "publishedTime": news_detail['publishedTime'],
    #         "categoryId": news_detail['categoryId'],
    #         "views": news_detail['views'],
    #         "relatedNews": jsonable_encoder(related_news),
    #     }"
    # }
