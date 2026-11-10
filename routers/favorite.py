from fastapi import Depends, HTTPException
from configs.db_config import get_db
from schemas.base import NewsItemBase
from utils.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from models.users import User
from fastapi import APIRouter, Query
from crud import favorite
from schemas.favotite import FavoriteAddRequest, FavoriteCreate, FavoriteListResponse, FavoriteItemResponse
from fastapi import status

from utils.response import success_response
router = APIRouter(prefix="/api/favorite",tags=["favorite"])

# 检查新闻收藏状态
@router.get("/check")
async def check_favorite(news_id:int=Query(...,alias = "newsId"),
                         user:User = Depends(get_current_user),
                         db:  AsyncSession = Depends(get_db)
                         ):
    
    is_favorite = await  favorite.is_news_favorite(db,user.id,news_id)
    return success_response(message = "收藏成功",data = FavoriteCreate(isFavorite = is_favorite))

# 新增收藏列表
@router.post("/add")
async def add_favorite(
    data:FavoriteAddRequest,
    user:User = Depends(get_current_user),
    db:  AsyncSession = Depends(get_db)
                      ):
    # 添加收藏
    result = await favorite.add_news_favorite(db,user.id,data.news_id)

    # 统一走响应模型输出 camelCase，不再直接吐 ORM 对象
    return success_response(message = "收藏成功",data = FavoriteItemResponse.model_validate(result))


# 取消收藏
@router.delete("/remove")
async def remove_favorite(news_id:int = Query(...,alias = "newsId"),
                          user:User = Depends(get_current_user),
                          db:  AsyncSession = Depends(get_db)
                          ):
    result = await  favorite.remove_news_favorite(db,user.id,news_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="取消收藏失败")
    return success_response(message = "取消收藏成功")


@router.get("/list")
async def get_favorite_list(
    page:int = Query(1,ge =1),
    page_size:int = Query(10,alias = "pageSize"),
    
    user:User = Depends(get_current_user),
    db:  AsyncSession = Depends(get_db)):
    # 获取收藏列表
    rows,total = await favorite.get_favorite_list(db,user.id,page,page_size)
    favorite_list = [{**news.__dict__,"favorite_time":favorite_time,"favorite_id":favorite_id}for news ,favorite_time,favorite_id in rows]
    has_more = total>page*page_size
    data = FavoriteListResponse(list = favorite_list,total = total,has_more = has_more)
    return success_response(message = "收藏成功",data = data)
# 清空收藏列表
@router.delete("/clear")
async def clear_favorite(user:User = Depends(get_current_user),db:  AsyncSession = Depends(get_db)):
    # 执行清空函数
    total = await favorite.remove_all_favorites(db=db,user_id=user.id)
    return success_response(message = f"成功清除{total}条记录")
 