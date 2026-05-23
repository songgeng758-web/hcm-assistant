"""
通用能力模块 · API 路由

包含：
- 字段映射
- 校验规则库
- 操作日志
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
def ping():
    """通用能力模块心跳"""
    return {"module": "common", "status": "ok"}


# TODO: 下一步实现
# POST /validators/id-card        身份证校验
# POST /validators/phone          手机号校验
# GET  /field-mappings            查询字段映射配置
# POST /field-mappings            保存字段映射配置
