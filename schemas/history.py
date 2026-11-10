from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field 
from schemas.base import NewsItemBase
class HistoryAddRequest(BaseModel):
    news_id:int = Field(...,alias = "newsId")
    
class HistoryAddResponse(BaseModel):
    id:int = Field(alias = "id")
    user_id:int = Field(alias = "userId")
    news_id:int = Field(alias = "newsId")
    view_time:datetime = Field(alias = "viewTime")
    
    model_config = ConfigDict(
            populate_by_name=True,
            from_attributes=True
        )
    
# 定义返回结果列表项的模型
class HistoryList(NewsItemBase):
    history_id:int = Field(alias = "historyId")
    view_time:datetime = Field(alias = "viewTime")
    model_config = ConfigDict(
            populate_by_name=True,
            from_attributes=True
        )
    
# 定义获取浏览历史的返回结果数据类型 
class HistoryGetResponse(BaseModel):
    list:list[HistoryList]
    total:int
    has_more:bool = Field(alias = "hasMore")
    
    model_config = ConfigDict(
            populate_by_name=True,
            from_attributes=True
        )