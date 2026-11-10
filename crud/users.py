from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException,status

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User, UserToken
from schemas.users import UpdateUserInfoRequest,  UserRefreshTokenRequest, UserRefreshTokenResponse, RegisterReq,VaryfyEmailReq
from utils import security
from utils.security import get_hash_password
from cache.user_cache import delete_send_email_cache,get_send_email_cahce,set_user_cache, get_user_cache, delete_user_cache
from cache import user_cache
# 根据用户名查询数据库
async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


# 创建用户
async def create_user(db: AsyncSession, user_data:RegisterReq):
    # 先密码加密处理，然后新增数据到数据库 passlib 模块

    user = User(
        username=user_data.username,
        password=get_hash_password(user_data.password),  # 实际应用中应加密存储
        email = user_data.email
    )
    try:
        db.add(user)
        await db.commit()
        # refresh 表示从数据库中重新加载数据，确保返回的对象是最新的
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="添加用户失败，请重试")
    return user


# 恢复已注销的账户：没有重置密码的作用
async def restore_user(db: AsyncSession, user_data:VaryfyEmailReq ):
    # 1.校验验证码：缓存里存的是字符串，直接和用户提交的字符串比对
    code = await get_send_email_cahce(user_data.email)
    if not code :
        raise HTTPException(status_code=400,detail = "验证码已过期，请重新获取")
    if code != user_data.code.strip():
        # 输错一次就计数，返回剩余可尝试次数；<=0 表示已锁定
        left = await user_cache.set_email_varify_cache(user_data.email)
        if left <= 0:
            raise HTTPException(status_code=429,detail = "验证码错误次数过多，请十分钟后再试")
        raise HTTPException(status_code=400,detail = f"验证码错误，还可尝试{left}次")
    # 2.校验账号：必须是已注销、并且库里绑定的邮箱与提交的一致
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()
    if not user or user.email != user_data.email or not user.is_deleted:
        raise HTTPException(status_code = 401,detail = "用户名或邮箱不匹配，或该账号无需恢复")
    
    try:   
        user.is_deleted = False
        await db.commit()
        await db.refresh(user)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="账户恢复失败，请重试")
    await  user_cache.clear_cache(user_data.email)
    await delete_send_email_cache(user_data.email)
    
    


# 生成token
async def create_token(db: AsyncSession, user_id: int):
    result = await db.execute(select(UserToken).where(UserToken.user_id == user_id))
    token_data = result.scalar_one_or_none()

    # 生成访问令牌
    access_token = security.create_token(user_id)
    # 生成刷新令牌
    refresh_token = security.create_token(user_id, refresh=True)
    # 检查原本令牌是否存在，存在就更新，不存在新增
    if not token_data:
        token_data = UserToken(user_id=user_id,
                            access_token = access_token,
                            refresh_token = refresh_token,
                            )
        db.add(token_data)
    else:
        token_data.access_token = access_token
        token_data.refresh_token = refresh_token
    await db.commit()

    # 写入会话缓存：value 存最新 access_token，他处重新登录会覆盖，旧 token 随即失效
    await set_user_cache(user_id, access_token)
    return access_token,refresh_token

# 查询用户是否存在并验证密码是否正确
async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await get_user_by_username(db, username)
    if not user:
        return None
    # 已注销的账户不允许登录（对外统一提示"用户名或密码错误"，不泄露账号状态）
    if user.is_deleted:
        return None
    # 验证密码是否正确
    if not security.verify_password(password, user.password):
        return None
    return user

# 刷新访问令牌
async def refresh_access_token(db:AsyncSession,refresh_token:UserRefreshTokenRequest):
    query = select(UserToken).where(UserToken.refresh_token == refresh_token.refresh_token)
    result = await db.execute(query)
    token_data = result.scalar_one_or_none()
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌不正确，请重新登录")

    token = security.decode_token(refresh_token.refresh_token)
    if not token:
        # 过期或伪造：清掉库里这行，强制重新登录
        try:
            await db.delete(token_data)
            await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌已过期，请重新登录")

    # 会话白名单校验：注销/改密/登出会删除缓存，删了就不允许再刷新
    # 注意这里只判断"存在"，不能比对值——缓存里存的是 access_token，和 refresh_token 永远不相等
    user_id = int(token["sub"])
    if not await get_user_cache(user_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")

    if not token.get("refresh"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请提供刷新令牌")

    # 生成新的访问令牌和刷新令牌
    access_token = security.create_token(user_id)
    new_refresh_token = security.create_token(user_id, refresh=True)
    # 刷新令牌时候先更新缓存，如果先入库，再缓存，redIs抖动造成缓存失败，用户redis与数据库不一致，就会重新登陆
    await set_user_cache(user_id, access_token)
    # 更新数据库中的token
    try:
        query = update(UserToken).where(UserToken.id == token_data.id).values(access_token=access_token,refresh_token=new_refresh_token)
        await db.execute(query)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token入库失败，请重新尝试刷新")

    # 轮换后写入新 access_token，旧的 access token 下次请求会因缓存值不匹配而失效
    return UserRefreshTokenResponse(access_token=access_token,refresh_token=new_refresh_token)


# 更新用户数据
async def update_user(db: AsyncSession,username:str,user_data:UpdateUserInfoRequest,):
    # model_dump(exclude_unset=True, exclude_none=True)：没传的字段不更新
    values_dict = user_data.model_dump(exclude_unset=True, exclude_none=True)
    # pydantic 实例本身恒为真值，必须用解析后的字典判断是否为空
    if not values_dict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新字段不能为空")
    query = update(User).where(User.username == username).values(**values_dict)
    result = await db.execute(query)
    await db.commit()

    # 检查更新
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="用户不存在或者没有更新字段")

    updated_user = await get_user_by_username(db, username)
    return updated_user


# 修改用户密码
async def update_password(db: AsyncSession,user:User,old_password:str,new_password:str):

    # 验证旧密码是否正确,正确则新密码加密，修改密码

    if not security.verify_password(old_password,user.password) or new_password == old_password:
        return False
    hashed_new_password = security.get_hash_password(new_password)
    user.password = hashed_new_password
    try:
        await db.execute(delete(UserToken).where(UserToken.user_id == user.id))
        await db.commit()
        
        await db.refresh(user)
    except Exception as e:
        raise HTTPException(status_code=401,detail = "修改密码失败，请重试")
    await delete_user_cache(user.id)
    
    
    return True


# 退出登录：清缓存 + 删 token 行
async def logout(db: AsyncSession, user_id: int):
    await delete_user_cache(user_id)
    await db.execute(delete(UserToken).where(UserToken.user_id == user_id))
    await db.commit()


# 注销账户（软删除）：删会话缓存 + 删 token 行 + is_deleted=True
# 注销状态只由 user.is_deleted 记录，不再额外写 Redis 标记
async def cancel(db: AsyncSession, user_id: int):
    # 先删会话缓存：失败就直接报错，避免"库里已注销、token 还能用"的中间态
    result = await delete_user_cache(user_id)
    if not result:
        return False
    try:
        await db.execute(delete(UserToken).where(UserToken.user_id == user_id))
        await db.execute(update(User).where(User.id == user_id).values(is_deleted=True))
        await db.commit()
    except:
        await db.rollback()
        return False
    return True
