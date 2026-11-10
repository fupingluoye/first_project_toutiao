from cache.news_cache import set_cache_news_detail
from schemas.base import NewsItemBase,NewsDetail,CategoryItem

from cache.news_cache import get_cache_news_list, set_cache_news_list, set_cached_categories
from sqlalchemy import func, select, update
from cache.news_cache import updata_news_views
from sqlalchemy.ext.asyncio import AsyncSession

from cache.news_cache import get_cached_categories,get_cache_news_detail
from models.news import Category, News
from cache.news_cache import get_news_views
from cache.news_cache import get_all_news_views, get_many_news_views
# 定义方法，获取新闻分类
async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 10):
    # 先尝试从缓存中获取数据
    cache_categories = await get_cached_categories()
    if cache_categories:
        return cache_categories

    # 缓存中没有数据，从数据库中查询数据
    stmt = select(Category).offset(skip).limit(limit)
    result = await db.execute(stmt)
    categories = result.scalars().all()

    # 统一走 CategoryItem：只保留 id/name/sortOrder 三个字段（camelCase），
    # 不再把 created_at/updated_at 等内部字段漏进响应和缓存
    if categories:
        categories = [
            CategoryItem.model_validate(item).model_dump(mode="json", by_alias=True)
            for item in categories
        ]
        await set_cached_categories(categories)

    # 返回数据
    return categories


# 获取某个分类下的所有新闻
async def get_news_list(
    db: AsyncSession, category_id: int, skip: int = 0, limit: int = 10
):
    page = skip//limit +1
    # 先查找缓存中有没有新闻
    cached_list = await get_cache_news_list(category_id,page,limit)
    if cached_list:
        # 缓存命中：也走同一个 schema，保证和未命中路径返回的字段完全一致
        return [NewsItemBase.model_validate(item) for item in cached_list]

    # 查询的是指定分类下的所有新闻
    stmt = select(News).where(News.category_id == category_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    news_list = result.scalars().all()

    if news_list :
        # 先把orm数据转换为字典才可以写入缓存
        # orm -> pydantic -> dict；by_alias=True 让缓存里就是 camelCase，
        # 响应时不用再转换，前端拿到一套字段名
        news_data = [ NewsItemBase.model_validate(item).model_dump(mode="json",by_alias=True) for item in news_list]
        await set_cache_news_list(category_id,page,limit,news_data)
    return [NewsItemBase.model_validate(item) for item in news_list]


#查询某一类新闻的个数
async def get_news_count(db: AsyncSession, category_id: int):
    
    
    # 查询指定分类下的新闻总数
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one()  # one表示只能有一个结果，scalar表示返回的是一个标量值

# 查询某个新闻的细节详情
async def get_news_detail(db: AsyncSession, news_id: int):
    # 先查找缓存中有没有新闻
    cached_detail = await get_cache_news_detail(news_id)
    if cached_detail:
        # 由于存在存有空数据用来防止缓存穿透，所以要判断是否有error字段，有则直接返回
        if cached_detail.get("error"):
            return cached_detail
        # 缓存中存在数据，更新缓存，浏览量+1
        new_views = await updata_news_views(news_id)
        cached_detail["views"] = new_views
        return cached_detail  # 返回查询的数据，类型是字典
    
    # 用户缓存不存在则查数据库
    stmt = select(News).where(News.id == news_id)
    result = await db.execute(stmt)
    news_detail = result.scalar_one_or_none()
    # 将数据写入缓存
    if news_detail is None:
        news_detail_content = {"error":"数据不存在，请检查新闻id是否正确"}
        await set_cache_news_detail(news_id,news_detail_content)
        return news_detail_content
    
    news_detail_content = (NewsDetail.model_validate(news_detail).model_dump(mode="json",by_alias=True))
    if await get_news_views(news_id):
        news_detail_content["views"] = await get_news_views(news_id)
    await set_cache_news_detail(news_id,news_detail_content)
    new_views = await updata_news_views(news_id)
    news_detail_content["views"] = new_views
    return news_detail_content  # 返回一个对象，如果没有则返回None


# 定期进行缓存中数据入库
async def increase_news_views(db: AsyncSession, news_id: int):
    # 缓存中读取一个键的浏览量
    score = await get_news_views(news_id)
    if score is None:
        return False
    if int(score) % 6 ==0: 
        stmt = update(News).where(News.id == news_id).values(views=int(score))
        result = await db.execute(stmt)
        await db.commit()
    return int(score)


# 获取同类推荐新闻
async def get_related_news(
    db: AsyncSession, category_id: int, news_id: int, limit: int = 1
):
    stmt = (
        select(News)
        .where(News.category_id == category_id, News.id != news_id)
        .order_by(News.views.desc(), News.publish_time.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    # return result.scalars().all()
    related_news = result.scalars().all()
    # 列表推导式，推导出新闻核心数据，然后return
    # key 统一 camelCase，与列表/详情接口同一套命名（publishTime/categoryId）
    return [
        {
            "id": news_detail.id,
            "title": news_detail.title,
            "content": news_detail.content,
            "image": news_detail.image,
            "author": news_detail.author,
            "publishTime": news_detail.publish_time,
            "categoryId": news_detail.category_id,
            "views": news_detail.views,
        }
        for news_detail in related_news
    ]

# 定时任务调用：把 Redis 里累计的浏览量批量写回数据库（幂等，只更新有变化的行）
async def flush_news_views_to_db(db: AsyncSession):
    pairs = await get_all_news_views()
    if not pairs:
        return 0
    rows = await db.execute(
        select(News.id, News.views).where(News.id.in_([news_id for news_id, _ in pairs]))
    )
    db_views = dict(rows.all())
    changed = [
        {"id": news_id, "views": views}
        for news_id, views in pairs
        if db_views.get(news_id) != views
    ]
    if not changed:
        return 0
    await db.execute(update(News), changed)
    await db.commit()
    return len(changed)
