"""
全项目唯一的声明式基类。

为什么必须只有一个 Base：
DeclarativeBase 的每个直接子类都会自动获得一份独立的 MetaData，
Base.metadata 就是"表登记簿"。如果 users.py / history.py / favorite.py
各自写一个 class Base(DeclarativeBase)，就会产生 4 本互不相通的登记簿，
alembic autogenerate 只能看到其中一本，生成的迁移就会缺表。
"""

from datetime import datetime,timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型共用这一个基类。"""


class TimestampMixin:
    """
    公共时间列 mixin。

    mixin 里的 mapped_column 会被复制到每个继承它的表，
    news / news_category 原来就是靠 Base 自带这两列实现的，行为保持不变。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="更新时间"
    )
