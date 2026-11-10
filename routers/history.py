from configs.db_config import get_db
from models.users import User
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from crud import history
from schemas.history import HistoryAddRequest,HistoryAddResponse,HistoryGetResponse
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/history",tags=["history"])

# 定义接口，增加浏览历史记录
@router.post("/add")
async def add_history(data:HistoryAddRequest,
                      db: AsyncSession = Depends(get_db),
                      user:User = Depends(get_current_user)):
    # 增加浏览历史记录，函数的返回结果是一个History对象,user
    result = await history.add_history(data,db,user)
    
    return success_response(message = "添加成功",data=HistoryAddResponse.model_validate(result))
    
    
# 定义接口，获取浏览历史记录
@router.get("/list")
async def get_history_list(page:int = Query(1,ge =1),page_size:int = Query(10,ge=1,alias = "pageSize"),
                           db: AsyncSession = Depends(get_db),
                           user:User = Depends(get_current_user)):
    total,result = await history.get_history(db,user.id,page,page_size)
    lists = [{**item.__dict__,
              "view_time":news_time,
              "history_id":history_id}for item,news_time,history_id in result]
    has_more = total > page * page_size
    response_data = HistoryGetResponse(list=lists,total = total,hasMore = has_more)
    return success_response(data = response_data)


# 定义接口，删除某条浏览记录
@router.delete("/delete/{history_id}")
async def delete_history_one(history_id:int,user:User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db),
                            ):
    # 参传来某一条历史记录id
    result = await history.delete_history_one(db,history_id,user.id)
    if not result:
        raise HTTPException(status_code=404,detail="记录不存在")
    return success_response(message="删除成功")


# 定义接口，清空浏览历史记录
@router.delete("/clear")
async def clear_history(user:User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
                            result = await history.delete_history_clear(db,user.id)
                            if not result:
                                raise HTTPException(status_code=404,detail="清空失败")
                            return success_response(message="清空成功")