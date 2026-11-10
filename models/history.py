from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer,UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    # 仅类型检查用； 字符串解析，避免循环导入
    from models.users import User


class History(Base):
    '''  浏览历史orm模型'''

    __tablename__ = "history"
    # 创建索引
    __table_args__ = (
                    UniqueConstraint("user_id","news_id",name ="union_idx_userid_newsid"),
                    Index("idx_user_id","user_id"),
                    Index('idx_view_time','view_time'),
                    Index("idx_news_id","news_id"),
                    )
    id :Mapped[int] = mapped_column(Integer,primary_key = True,autoincrement = True,comment = '历史ID')
    user_id :Mapped[int] = mapped_column(Integer,ForeignKey("user.id"),nullable = False,comment = "用户ID")
    news_id :Mapped[int] = mapped_column(Integer,ForeignKey("news.id"),nullable = False,comment = "新闻ID")
    view_time :Mapped[datetime] = mapped_column(DateTime,default = lambda:datetime.now(timezone.utc),comment = "浏览时间")
    user:Mapped["User"]=relationship(back_populates="history")
    def __repr__(self):
        return f"<History(id={self.id},user_id={self.user_id},news_id={self.news_id},view_time={self.view_time})>"
