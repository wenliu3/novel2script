"""novel2script — 小说转剧本系统。

FastAPI 入口。
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("novel2script 启动")
    for d in ("uploads", "output"):
        Path(d).mkdir(parents=True, exist_ok=True)
    # 在 lifespan 中挂载静态文件，确保目录已创建
    app.mount("/output", StaticFiles(directory="output"), name="output")
    yield
    logger.info("novel2script 关闭")


app = FastAPI(
    title="Novel2Script",
    description="中文小说 → LRM 剧本转换",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"service": "novel2script", "version": "2.0.0", "status": "running", "docs": "/docs"}
