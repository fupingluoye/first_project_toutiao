from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    # 仅类型检查用；运行时靠 "user.id" / "news.id" / "User" 字符串解析
    from models.users import User


class Favorite(Base):
    """
    收藏表ORM模型
    """
    __tablename__ = 'favorite'

    # 创建索引
    # UniqueConstraint: 唯一约束, 当前用户，当前新闻，只能收藏一次
    # Index('idx_news_id'): 外键列索引，MySQL 要求外键列上必须有索引
    #   （user_id 不用单独建：user_news_unique 的最左前缀就是 user_id）
    __table_args__ = (
        UniqueConstraint('user_id', 'news_id', name='user_news_unique'),
        Index('idx_news_id', 'news_id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="收藏ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey("news.id"), nullable=False, comment="新闻ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="收藏时间")
    user:Mapped["User"] = relationship(back_populates="favorite")
    
    def __repr__(self):
        return f"<Favorite(id={self.id}, user_id={self.user_id}, news_id={self.news_id}, created_at={self.created_at})>"
