from passlib.context import CryptContext
import jwt
from config import Config
from datetime import datetime, timedelta, timezone
from celerys import celery_task1


ACCESS_TOKEN_EXPIRE_MINUTES =  30
REFRESH_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60
JWT_SECRET_KEY = Config.JWT_SECRET_KEY
JWT_ALGORITHM = Config.JWT_ALGORITHM
import random
import uuid
# 创建密码上下文对象，指定加密算法
# bcrypt 是一种常用的哈希算法，适合用于密码存储,第二个参数表示过时的算法，auto 表示自动处理过时的算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 密码加密
def get_hash_password(password: str):
    return pwd_context.hash(password)


# 密码验证,varify返回值是一个bool类型
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


# JWT令牌
# 生成令牌
def create_token(data:int ,expire_time:timedelta = timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES),role:str = "user",refresh:bool = False):
    # 刷新令牌统一使用 REFRESH_TOKEN_EXPIRE_MINUTES，忽略调用方传入的 expire_time，避免两处时长不一致
    if refresh:
        expire_time = timedelta(minutes = REFRESH_TOKEN_EXPIRE_MINUTES)
    exp = datetime.now(timezone.utc) + expire_time
    payload = {}
    payload["exp"] = exp
    payload["role"] = role 
    payload["sub"] = str(data)
    payload["jti"] = str(uuid.uuid4())
    payload["refresh"] = refresh
    result =  jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return result

# 解码令牌
# 只负责纯 JWT 解码，不做任何 IO（缓存/数据库校验由调用方负责）
# 返回值约定：dict = 解码成功；None = 已过期；False = 伪造/格式错误
def decode_token(token:str):
    try:
        payload =  jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if "sub" not in payload:
            return False
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return False
# 定义工具，生成随机六位数验证码
def generate_code():
    return f'{random.randint(100000,999999)}'
    
    
# 定义工具函数，发送邮箱
def send_email_code(to_email:str,code:int):
    return celery_task1.send_email.delay(to_email=to_email,code=code)