from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str = "success", data=None):
    content = {"code": 200, "message": message, "data": data}
    # 目标，把任何fastapi对象，pydantic,orm对象都正常响应
    # 解决：使用jsonable_encoder将对象转换为可序列化的字典
    # 然后使用JSONResponse把字典转换为JSON响应
    return JSONResponse(content=jsonable_encoder(content))
