from configs import cache_conf

# 会话存活时长（秒），与 security.REFRESH_TOKEN_EXPIRE_MINUTES 保持一致
SESSION_EXPIRE_SECONDS = 7 * 24 * 60 * 60


async def set_user_cache(user_id: int, access_token: str, expire: int = SESSION_EXPIRE_SECONDS):
    """
    写入/覆盖该用户的会话缓存。
    """
    await cache_conf.set_cache(f"user:{user_id}", access_token, expire)


async def get_user_cache(user_id: int):
    """
    读取该用户的会话缓存，返回 access_token 字符串；key 不存在返回 None。
    使用严格模式：Redis 故障会抛异常（表现为服务错误），
    不会被上层误判成"用户未登录"而把所有人踢下线。
    """
    return await cache_conf.get_cache(f"user:{user_id}")


async def delete_user_cache(user_id: int):
    """删除该用户的会话缓存，让旧 token 立即失效"""
    return await cache_conf.delete_cache(f"user:{user_id}")

# 定义函数，邮箱验证码缓存（验证码本身 5 分钟有效，同时写入 60 秒发送冷却）
async def set_send_email_cahce(email:str,code:str):
    send_key = f"send_email:{email}"
    if not await cache_conf.set_cache(send_key,code,60*5):
        return False
    if not await set_email_limit_cache(email):
        return False
    return True
    
# 定义函数，读取邮箱验证码缓存
async def get_send_email_cahce(email:str):
    key = f"send_email:{email}"
    return await cache_conf.get_cache(key)

# 删除缓存，每次验证完成就删除
async def delete_send_email_cache(email:str):
    key = f"send_email:{email}"
    return await cache_conf.delete_cache(key)

# 邮箱验证码冷却缓存
async def set_email_limit_cache(email:str,expire:int = 60):
    key = f"limit_email:{email}"
    return await cache_conf.set_cache(key,1,expire)
async def get_email_limit_cache(email:str):
    key = f"limit_email:{email}"
    return await cache_conf.get_cache(key)

# 冷却剩余秒数：<=0 表示不在冷却期，可以发送
async def get_email_limit_ttl(email:str):
    ttl = await cache_conf.query_key_ttl(f"limit_email:{email}")
    return ttl if ttl > 0 else 0

# 删除冷却缓存 
async def delete_email_limit_cache(email:str):
    key = f"limit_email:{email}"
    return await cache_conf.delete_cache(key)
# 验证码最多允许输错的次数、以及达到上限后的锁定时长（秒，与提示文案"十分钟"一致）
MAX_VERIFY_FAIL = 5
VERIFY_LOCK_SECONDS = 600

# 记录一次验证码校验失败，返回剩余可尝试次数；返回值 <= 0 表示已被锁定
async def set_email_varify_cache(email:str):
    key = f"varified_email:{email}"
    varify_num = await cache_conf.incrby_cache(key)
    # Redis 故障时 incrby_cache 返回 False，此时不锁用户，只当作本次输错
    if not varify_num:
        return MAX_VERIFY_FAIL - 1
    # 只有第一次输错才设置过期时间，之后的自增不续期，锁定时长从第一次输错开始算
    if varify_num == 1:
        await cache_conf.expire_cache(key,VERIFY_LOCK_SECONDS)
    return MAX_VERIFY_FAIL - varify_num

async def clear_cache(email:str):
    key = f"varified_email:{email}"
    return await cache_conf.delete_cache(key)