from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
class RegisterReq(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    email:str = Field(...,pattern=r".+@qq\.com$", description=" 邮箱")

class UserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    
class VaryfyEmailReq(BaseModel):
    username:str= Field(..., min_length=3, max_length=50)
    email:str= Field(...,pattern=r".+@qq\.com$",min_length=6, max_length=100)
    code:str = Field(...,min_length=6,max_length=6,pattern = r"^\d{6}$")
# 用户信息基础数据模型（作为响应模型的基类，gender 保持宽泛，
# 兼容数据库中已存在的 unknown 默认值，否则老用户查询会校验失败）
class UserInfoBase(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")



#更新用户信息的模型类
class UpdateUserInfoRequest(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    # 输入只允许 male/female，其他值直接 422，到不了数据库
    gender: Optional[Literal["male", "female"]] = Field(None, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    
# 修改用户密码
class UserChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, description="旧密码",alias='oldPassword')
    new_password: str = Field(..., min_length=6, description="新密码",alias='newPassword')
    model_config = ConfigDict(
        populate_by_name=True,  # 允许使用别名进行数据填充
    )  # 将下划线命名转换为驼峰命名

class UserRefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="刷新令牌")

# 定义user_info对应的类
class UserInfoResponse(UserInfoBase):
    id: int
    username: str
    # 模型类配置
    model_config = ConfigDict(
        from_attributes=True,  # 允许从orm对象属性中填充数据
    )  # 将下划线命名转换为驼峰命名


# data自己的数据类型
class UserAuthResponse(BaseModel):
    # 别名统一 camelCase：前端所有接口只按一套命名取值
    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    user_info: UserInfoResponse = Field(
        ..., alias="userInfo"
    )  # 使用别名userInfo来匹配前端的字段名

    # 模型类配置
    model_config = ConfigDict(
        populate_by_name=True,  # 允许使用别名进行数据填充
        from_attributes=True,  # 允许从orm对象属性获取数据
    )  # 将下划线命名转换为驼峰命名


# 定义token返回模型
class UserRefreshTokenResponse(BaseModel):
    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    model_config = ConfigDict(
        populate_by_name=True,  # crud 里用字段名构造，响应时输出别名
    )