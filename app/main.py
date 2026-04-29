from __future__ import annotations

"""
医院自动回访系统 — 主入口
"""

import logging

import uvicorn
from fastapi import FastAPI

from app.api.routes import router as api_router
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title=settings.app_name,
    description="基于 Agent 的医院自动回访系统 — 根据病人病例和最近治疗情况自动拨打电话了解康复情况",
    version="0.1.0",
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }


def main():
    """启动服务"""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
