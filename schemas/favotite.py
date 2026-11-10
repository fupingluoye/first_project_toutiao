from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from models.favorite import Favorite
from schemas.base import NewsItemBase

class FavoriteCreate(BaseModel):
    '''  新闻的收藏状态pydantic模型'''
    is_favorite:bool = Field(...,alias = "isFavorite")
    
# 添加收藏请求体参数
class  FavoriteAddRequest(BaseModel):
    ''' 传入新闻id，收藏某条新闻'''
    news_id :int = Field(...,alias = "newsId")


# 添加收藏的响应模型：不再直接吐 ORM 对象（那会输出 snake_case），统一 camelCase
class FavoriteItemResponse(BaseModel):
    id: int
    user_id: int = Field(alias="userId")
    news_id: int = Field(alias="newsId")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    
    
#定义收藏列表项的类
class FavoriteNewsItemResponse(NewsItemBase):
    '''   '''
    favorite_id:int = Field(alias = "favoriteId")
    favorite_time:datetime = Field(alias = "favoriteTime")
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    
    
    

# 定义响应类型,收藏列表接口
class FavoriteListResponse(BaseModel):
    list:list[FavoriteNewsItemResponse]
    total:int
    has_more:bool = Field(alias = "hasMore")
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )