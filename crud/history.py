
from models.news import News
from models.users import User
from datetime import datetime, timezone
from sqlalchemy import delete, func, select
from models.history import History
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.history import HistoryAddRequest

# 增加浏览历史
# 思路  验证用户是否登录， 登录的化查看用户是否浏览过当前新闻，浏览过就跟新浏览时间，没有就新增浏览数据
async def add_history(history:HistoryAddRequest,db:AsyncSession,user:User):
    stmt = select(History).where(History.news_id == history.news_id,History.user_id == user.id)
    result = await db.execute(stmt)
    exixt_history = result.scalar_one_or_none()
    if  exixt_history:
        exixt_history.view_time = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(exixt_history)
        return exixt_history
    history = History(user_id = user.id,news_id = history.news_id)
    db.add(history)
    await db.commit()
    query = select(History).where(History.news_id == history.news_id,History.user_id == user.id)
    await db.execute(query)
    await db.commit()
    await db.refresh(history)
    return history
    
    
# 定义函数，获取浏览历史记录
# 思路，验证用户是否登录，登陆上了，统计总量，连表查询浏览历史记录，
async def get_history(db:AsyncSession,user_id:int,page:int =1,page_size:int = 10):
    # 查询浏览历史总量
    query = select(func.count()).where(History.user_id == user_id)
    result = await db.execute(query)
    total = result.scalar_one()
    offset = (page -1) * page_size
    stmt = (select(News,History.view_time.label("view_time"),
                   History.id.label("history_id")).join(History,History.news_id == News.id)
            .where(History.user_id == user_id).order_by(History.view_time.desc())
            .offset(offset).limit(page_size)
            )
    result = await db.execute(stmt)
    result_history = result.all()
    
    return total,result_history


# 定义函数实现删除单条记录的功能
async def delete_history_one(db:AsyncSession,history_id,user_id:int):
   
    stmt =delete(History).where(History.id == history_id,History.user_id == user_id)
    
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount> 0
    
    
# 清空浏览历史记录
async def delete_history_clear(db:AsyncSession,user_id:int):
    stmt = delete(History).where(History.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount> 0
