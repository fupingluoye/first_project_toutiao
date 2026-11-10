# 新闻相关的缓存方法，新闻分类的读取和写入
# 读取新闻分类缓存
from typing import Any, Dict, List, Optional
from configs import cache_conf as cc
NEWS_LIST_PREFIX= "news_list"
# 新闻分类缓存key
CATEGOTIES_KEY = "news:categoties"
EXPIRE_TIME = 7200
NOT_DETAIL_EXPIRE_TIME = 600
NEWS_DETAILED_KEY = "news:details"
VIEWS_KEY = "news:views"
# 读取新闻分类缓存
async def get_cached_categories():
    return await cc.get_json_cache(CATEGOTIES_KEY)

# 定义方法，写入新闻分类缓存
async def set_cached_categories(data:List[Dict[str,Any]],expire:int=EXPIRE_TIME):
    return await cc.set_cache(CATEGOTIES_KEY,data,expire)


# 新闻列表数据的缓存，读取和写入
# 写入缓存 key 是news_list:分类id:页码：每页数量 
async def set_cache_news_list(category_id:Optional[int],page:int,size:int,news_list:List[Dict[str,Any]],expire:int = EXPIRE_TIME):
    category_part =category_id if category_id is not None else "all"
    key = f"{NEWS_LIST_PREFIX}{category_part}:{page}:{size}"
    return await cc.set_cache(key,news_list,expire)
    
    
# 读取缓存
async def get_cache_news_list(category_id:Optional[int],page:int,size:int):
    category_part =category_id if category_id is not None else "all"
    key = f"{NEWS_LIST_PREFIX}{category_part}:{page}:{size}"
    return await cc.get_json_cache(key)

# 定义新闻详情缓存查询
async def get_cache_news_detail(news_id:int):
    key = f"{NEWS_DETAILED_KEY}:{news_id}"
    return await cc.get_json_cache(key)

# 定义新闻缓存详情写入
async def set_cache_news_detail(news_id:int,news_detail:Optional[dict],expire:int=EXPIRE_TIME):
    key = f"{NEWS_DETAILED_KEY}:{news_id}"
    # 数据库没有数据，过期时间为600秒,预防缓存穿透问题
    if  news_detail == {"error":"数据不存在，请检查新闻id是否正确"}:
        # 设置过期时间
        expire = NOT_DETAIL_EXPIRE_TIME
        await cc.set_cache(key,news_detail,expire)
        return
        
    await cc.set_cache(key,news_detail,expire)
    
    await cc.set_news_detail_views(f"{VIEWS_KEY}:",news_id,news_detail["views"])

# 更新缓存浏览量
async def updata_news_views(news_id:int,score:int = 1):
    
    key = f"{VIEWS_KEY}:"
    return await cc.update_news_views(key,news_id,score)


# 定义函数，查询一个新闻的浏览量
async def get_news_views(news_id:int):
    
    key = f"{VIEWS_KEY}:"
    return await cc.query_news_views(key,news_id)

# 批量读取全部累计浏览量（定时落库用），返回 [(news_id, views), ...]
async def get_all_news_views():
    raw = await cc.redis_client.zrange(f"{VIEWS_KEY}:", 0, -1, withscores=True)
    return [(int(news_id), int(score)) for news_id, score in raw]


# 批量读取指定新闻的最新浏览量，一次往返；Redis 里没有的返回 None
async def get_many_news_views(news_ids:list[int]):
    if not news_ids:
        return []
    raw = await cc.redis_client.zmscore(f"{VIEWS_KEY}:", news_ids)
    return [None if score is None else int(score) for score in raw]
