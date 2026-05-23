"""
HCM Assistant · 后端入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import org, payroll, common
from app.core.config import settings

app = FastAPI(
    title="HCM Assistant API",
    description="HCM 实施助手 - 面向实施顾问的数据迁移与校验工具",
    version="0.1.0",
)

# CORS 配置（前端开发联调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(org.router, prefix="/api/org", tags=["组织人事"])
app.include_router(payroll.router, prefix="/api/payroll", tags=["薪酬计算"])
app.include_router(common.router, prefix="/api/common", tags=["通用能力"])


@app.get("/")
def root():
    return {
        "name": "HCM Assistant",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
