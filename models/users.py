from datetime import datetime,timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    # 只在类型检查（IDE 提示）时导入，运行时不导入 —— 这是打破循环导入的关键。
    # 关系里的类名写成字符串，SQLAlchemy 在 mapper 配置阶段按类名去注册表里查。
    from models.favorite import Favorite
    from models.history import History


class User(Base):
    """
    用户信息表ORM模型
    """

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="用户ID"
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="用户名"
    )
    password: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码（加密存储）"
    )
    nickname: Mapped[Optional[str]] = mapped_column(String(50), comment="昵称")
    avatar: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="头像URL",
        default="https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg",
    )
    gender: Mapped[Optional[str]] = mapped_column(
        Enum("male", "female"), comment="性别", default="male"
    )
    bio: Mapped[Optional[str]] = mapped_column(
        String(500), comment="个人简介", default="这个人很懒，什么都没留下"
    )
    email:Mapped[Optional[str]] = mapped_column(String(500),unique = True,comment = "邮箱",server_default= None)
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, comment="手机号"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="更新时间"
    )
    is_deleted:Mapped[bool]= mapped_column(
        default = False,comment="是否被删除"
    )
    # 一对一：注解必须写成 Mapped[...]，且前向引用用字符串（类在后面才定义）
    user_token: Mapped[Optional["UserToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    favorite:Mapped[list["Favorite"]] = relationship(back_populates="user",cascade="all,delete-orphan")
    history:Mapped[list["History"]] = relationship(back_populates="user",cascade="all,delete-orphan")
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', nickname='{self.nickname}')>"


class UserToken(Base):
    """
    用户令牌表ORM模型
    """

    __tablename__ = "user_token"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="令牌ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(User.id), nullable=False,unique = True, comment="用户ID"
    )
    access_token: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False, comment="访问令牌值"
    )
    refresh_token: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False, comment="刷新令牌值"
    )
   
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
    user: Mapped["User"] = relationship(back_populates="user_token")



    def __repr__(self):
        return (
            f"<UserToken(id={self.id}, user_id={self.user_id}, access_token='{self.access_token}')>"
        )
