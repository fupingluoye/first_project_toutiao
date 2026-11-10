from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, func 

from models.favorite import Favorite
from models.news import News

# 检查新闻收藏状态
async def is_news_favorite(db: AsyncSession,user_id:int,news_id:int):
    query = select(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    result = await db.execute(query)
    # 是否有收藏记录,加上is not none，转换为bool类型
    return result.scalar_one_or_none() is not None



# 添加收藏
async  def add_news_favorite(db: AsyncSession,user_id:int,news_id:int):
    # 实例化一个收藏对象
    favorite = Favorite(user_id = user_id,news_id = news_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)
    # 返回收藏对象
    return favorite

# 取消收藏
async def remove_news_favorite(db: AsyncSession,user_id:int,news_id:int):
    stmt = delete(Favorite).where(Favorite.user_id == user_id,Favorite.news_id == news_id)
    result = await db.execute(stmt)
    await db.commit()
    # 检查命中数量
    return result.rowcount > 0 



# 获取某个用户收藏列表
async def get_favorite_list(db: AsyncSession,user_id:int,page:int=1,page_size:int=10):
#    获取列表总量
    count_query = select(func.count()).where(Favorite.user_id == user_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    # 收藏的列表,连表查询，join新闻表，分页查询,收藏时间排序
    # join后面第一个参数是关联的表，第二个参数是两个表的链接条件，where 后面是查询条件，查询的是收藏表的用户id
    # 收藏的列表,连表查询，join新闻表，分页查询,收藏时间排序
    # 在join后面加入参数，表示的是内连接
    query = (select(News,Favorite.created_at.label("favorite_time"),Favorite.id.label("favorite_id"))
    .join(Favorite,Favorite.news_id == News.id)
    .where(Favorite.user_id == user_id).order_by(Favorite.created_at.desc())
    .offset((page-1)*page_size)
    .limit(page_size))
    
    
    result = await db.execute(query)
    # scalars只取（）里面第一个字段对象，如News对象，而select查询的结果是多个字段除了News对象，还有Favorite对象
    rows = result.all()
    return rows,total

# 清空当前用户的收藏列表
async def remove_all_favorites(db: AsyncSession,user_id:int):
    stmt = delete(Favorite).where(Favorite.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    # 返回命中条数，有条数就返回，没有就返回0
    return result.rowcount or 0
    
