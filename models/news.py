from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


# 创建新闻分类表模型
class Category(TimestampMixin, Base):
    '''  分类列表的orm模型'''
    __tablename__ = "news_category"
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="分类id"
    )
    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="分类名称"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="排序"
    )

    # 打印return结果
    def __repr__(self):
        return (
            f"<Category(id={self.id}),name={self.name},sort_order={self.sort_order})>"
        )


# 创建新闻表模型
class News(TimestampMixin, Base):
    ''' orm新闻表'''
    __tablename__ = "news"
    # 创建索引，参数1是自定义的索引名，参数2是索引的字段名
    __table_args__ = (
        Index("fk_news_category_idx", "category_id"),  # 高频查询
        Index("idx_publish_time", "publish_time"),  # 按发布时间排序
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="新闻id"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="新闻标题")
    description: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="新闻简介"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="新闻内容")
    image: Mapped[Optional[str]] = mapped_column(String(255), comment="封面图片URL")
    author: Mapped[str] = mapped_column(String(50), comment="作者")
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("news_category.id"), nullable=False, comment="分类id"
    )
    views: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="浏览量"
    )
    publish_time: Mapped[datetime] = mapped_column(
        DateTime, default=lambda:datetime.now(timezone.utc), nullable=False, comment="发布时间"
    )
