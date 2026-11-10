import json
from typing import Any

import redis.asyncio as redis

from config import Config

# 创建变量，保存redis服务器地址，以后redis服务器地址改变，只需要改变量的值
REDIS_HOST = Config.REDIS_HOST
REDIS_PORT = Config.REDIS_PORT
REDIS_DB = Config.REDIS_DB
REDIS_PASSWORD  =  Config.REDIS_PASSWORD
# 创建redis连接对象,decode_response 参数表示是否将字节解码为字符串
redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT,
    password=REDIS_PASSWORD, db=REDIS_DB, 
    decode_responses=True, protocol=2,
    socket_connect_timeout=4
)

# 设置缓存和读取缓存 （读取的数据是个字符串，读取的数据是个字典或者列表）
# 读取的数据是个字符串
async def get_cache(key: str):
    try:
        return await redis_client.get(key)
    except Exception as e:
        print(f"获取数据失败：{e}")
        return None


# 读取的数据类型是列表或者字典
async def get_json_cache(key: str):
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"获取数据失败：{e}")
        return None


# 设置缓存,时间默认单位 秒
async def set_cache(key: str, value: Any, expire:int):
    try:
        if isinstance(value, (dict, list)):
            # 转换为字符串再存,ensure_ascii =False 表示中文正常保存
            value = json.dumps(value, ensure_ascii=False)

        await redis_client.setex(key, expire, value)
        return True
    except Exception as e:
        print(f"设置缓存失败：{e}")
        return False
#设置缓存，功能是让键的值自增1 
async def incrby_cache(key:str):
    try:
        
        return await redis_client.incrby(key,1)
    except Exception as e:
        return False
 
# 设置删除缓存
async def delete_cache(key:str):
    try:
        await redis_client.delete(key)
        return True
    except Exception as e:
        print(f"删除缓存失败：{e}")
        return False


# 设置新闻浏览量缓存
async def  set_news_detail_views(key:str,news_id:int,score:int = 1):
    try:
        await redis_client.zadd(key,{news_id:score},nx=True)
    except :
        print(f"缓存设置失败")

# 新闻浏览量缓存+1
async def update_news_views(key:str,news_id:int,score:int = 1):
    try:
        return await redis_client.zincrby(key,score,news_id)
         
    except :
        print(f"缓存更新失败")
        return None


# 查询浏览量缓存中元素个数，来确定合适写入数据库
async def query_news_views(key:str,news_id:int):
   
    return await redis_client.zscore(key,news_id)
   

# 查看一个键剩余时间（秒）：-2 表示键不存在，-1 表示键存在但没有设置过期时间
async def query_key_ttl(key:str):
    return int(await redis_client.ttl(key))


# 给已存在的键设置/重设过期时间
async def expire_cache(key:str,seconds:int):
    try:
        await redis_client.expire(key,seconds)
        return True
    except Exception as e:
        print(f"设置过期时间失败：{e}")
        return False