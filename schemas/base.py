
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class NewsItemBase(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    category_id: int = Field(alias="categoryId")
    views: int
    publish_time: Optional[datetime] = Field(None, alias="publishedTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


# 新闻分类响应模型：统一走 camelCase（sortOrder），与列表/详情接口保持同一套命名
class CategoryItem(BaseModel):
    id: int
    name: str
    sort_order: int = Field(0, alias="sortOrder")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

    
    
class NewsDetail(NewsItemBase):
    content:str
    
    model_config = ConfigDict(extra="ignore",
                              validate_by_name=True,
                              validate_by_alias=True)