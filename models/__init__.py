"""
models 包入口：导入即注册全部 ORM 模型。

注意顺序无关（各模型之间已无运行时互相 import），
但这里集中导入可以保证「只 import models 就能拿到完整元数据」，
alembic env.py 就是靠这一行把 5 张表都登记到 Base.metadata 上的。
"""

from models.base import Base, TimestampMixin
from models.favorite import Favorite
from models.history import History
from models.news import Category, News
from models.users import User, UserToken

__all__ = [
    "Base",
    "TimestampMixin",
    "Category",
    "News",
    "User",
    "UserToken",
    "History",
    "Favorite",
]
