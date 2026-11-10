from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from cache import user_cache
from configs.db_config import get_db
from crud import users
from models.users import User
from schemas.users import VaryfyEmailReq,RegisterReq,UpdateUserInfoRequest, UserAuthResponse, UserChangePasswordRequest, UserInfoResponse, UserRequest, UserRefreshTokenRequest
from utils.auth import get_current_user
from utils.response import success_response
from utils.security import generate_code,send_email_code
router = APIRouter(prefix="/api/user", tags=["users"])


# 注册账户接口
@router.post("/register")
async def register(user_data: RegisterReq, db: AsyncSession = Depends(get_db)):
    # 实现注册逻辑思路  1.验证用户名是否存在 2 创建用户  3 相应结果
    existing_user = await users.get_user_by_username(db, user_data.username)
    if existing_user:
        # 正常存在的用户：直接拒绝
        if not existing_user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在"
            )
        # 已注销的用户：，可以进行恢复账号，第一步先发送邮箱验证，然后等待结果
        if not  existing_user.email :
            raise HTTPException(status_code=409,detail = "没有绑定邮箱，无法恢复账号")
        # 冷却期内不允许重复发送，这里拿到的是剩余秒数
        left_seconds = await  user_cache.get_email_limit_ttl(existing_user.email)
        if left_seconds > 0:
            raise HTTPException(status_code=429,detail=f"暂时无法发送邮箱，请在{left_seconds}秒后重试")
        code = generate_code()
        if not await user_cache.set_send_email_cahce(existing_user.email,code):
            raise HTTPException(status_code=500,detail = "验证码保存失败，请稍后重试")
        try:
            await run_in_threadpool(send_email_code,existing_user.email,code)
            
        except Exception:
            # 发信失败：验证码作废，删掉这个用户永远收不到的码；
            # 60 秒发送冷却保留（两次发送动作之间至少隔 60 秒，无论成败，防故障期间被高频重试）
            await user_cache.delete_send_email_cache(existing_user.email)
            raise HTTPException(status_code=500,detail = "邮箱发送失败，请60秒后再试")
        # 重新发码时清掉上一次的错误计数，否则被锁过的账号拿到新码也验证不过
        await user_cache.clear_cache(existing_user.email)

        raise HTTPException(status_code=409,detail=" 你账号已注销，已发送邮箱验证码，继续完成验证")
    # 全新用户：插入新行
    await users.create_user(db, user_data)
    return success_response(message="注册成功")
@router.post("/varify_email")
async def varify_restore_user(user_data:VaryfyEmailReq,db:AsyncSession = Depends(get_db)):
    await users.restore_user(user_data=user_data,db = db)
    
    return success_response(message="恢复账号成功，请登录：")    
    
# 登录账户接口
@router.post("/login")
async def login(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    # 登录逻辑思路 1.验证用户名是否存在 2.验证密码是否正确 3.生成token并写入缓存 4.响应结果
    user = await users.authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误或用户不存在"
        )
    # create_token 内部已提交数据库并写入会话缓存
    access_token,refresh_token = await users.create_token(db, user.id)
    response_data = UserAuthResponse(
        access_token=access_token, refresh_token=refresh_token, userInfo=UserInfoResponse.model_validate(user)
    )
    return success_response(message="登录成功", data=response_data)

# 定义接口， 访问令牌刷新接口
@router.post("/refresh")
async def get_new_token(refresh_token_data:UserRefreshTokenRequest,db: AsyncSession = Depends(get_db)):
    # refresh_access_token 内部已处理缓存写入，失败时直接抛出异常
    result = await users.refresh_access_token(db,refresh_token_data)
    return success_response(message="刷新令牌成功",data=result)

# 获取个人信息
@router.get("/info")
async def get_user_info(user=Depends(get_current_user)):
    # 查token,封装crud，功能整合为一个函数，

    return success_response(
        message="获取用户信息成功", data=UserInfoResponse.model_validate(user)
    )

# 修改用户信息，用Put方法，验证token，然后跟新数据 响应结果
@router.put("/update")
async def update_user_info(user_data:UpdateUserInfoRequest,db: AsyncSession = Depends(get_db),user=Depends(get_current_user)):
    # 验证token，更新用户信息
    user = await users.update_user(db,user.username,user_data)
    return success_response(message="更新用户信息成功",data=UserInfoResponse.model_validate(user))

# 修改用户密码
@router.put("/password")
async def update_password(password_data:UserChangePasswordRequest,db: AsyncSession = Depends(get_db),user:User=Depends(get_current_user)):
    # 验证旧密码是否正确,正确则新密码加密，更新密码
    # update_password 成功后会清缓存并删除 token 行，所有旧 token 立即失效
    res_change_pwd = await users.update_password(db,user,password_data.old_password,password_data.new_password)
    if not res_change_pwd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误或新密码与旧密码相同"
        )
    return success_response(message="更新用户密码成功")

# 退出登录：清会话缓存 + 删 token 行，当前 access token 立即失效
@router.delete("/logout")
async def logout(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await users.logout(db, user.id)
    return success_response(message="退出登录成功")


# 注销账户：软删除，清会话缓存 + 删 token 行，之后该账号无法登录
@router.delete("/cancel")
async def cancel_user(db:AsyncSession = Depends(get_db),user:User = Depends(get_current_user)):
    result = await users.cancel(db, user.id)
    if result:
        return success_response(message="账号已注销")
    else:
        raise HTTPException(status_code = 500,detail = {"error":"注销失败，请重新尝试一下"})