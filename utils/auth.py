from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from fastapi.security import HTTPBearer
from configs.db_config import get_db
from cache.user_cache import get_user_cache
from models.users import User
from utils import security


class AuthToken(HTTPBearer):
    def __init__(self,auto_error = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self,request:Request):
        creds = await super().__call__(request)
        token = security.decode_token(creds.credentials)
        # token 可能的情况：None=过期  False=伪造/格式错误  dict=解码成功
        if  not self.verify_token(token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="token验证失败")
        if not self.verify_token_data(token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="角色权限不足")
        # 会话校验：缓存 user:{user_id} 保存该用户当前有效的 access_token
        # 改密码/注销/登出/他处重新登录都会删除或覆盖缓存，使旧 token 立即失效
        cached_token = await get_user_cache(int(token["sub"]))
        if not cached_token or cached_token != creds.credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="登录已失效，请重新登录")
        
        
        return token

    def verify_token_data(self,token):
            raise NotImplementedError("子类必须实现verify_token_data方法")

    def verify_token(self,token):
        if token:
            return True
        else:
            return False
# 验证用户角色是否有权限
class AccessAuthToken(AuthToken):
    def __init__(self,auto_error = True):
        super().__init__(auto_error=auto_error)
    def verify_token_data(self,token):
        if token and token.get("role") == "user"  and token.get("refresh") is False:
            return True
        else:
            return False

async def get_current_user(db:AsyncSession = Depends(get_db),token = Depends(AccessAuthToken())):
    user_id = token["sub"]
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    # 已注销（软删除）的账号即使还拿着有效 token 也不允许继续访问
    if not user or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="账号不存在或已注销")
    return user
