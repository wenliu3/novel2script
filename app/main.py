"""FastAPI 应用入口。

启动 FastAPI 服务，注册路由，管理应用生命周期。
提供 CORS 和静态文件支持。
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.services.config import load_settings
from app.utils.file_utils import ensure_dir
from app.utils.logger import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    setup_logging(verbose=False)
    logger.info("novel2script API 启动中...")

    # 确保必要目录存在
    for d in ("uploads", "output", "novels"):
        ensure_dir(Path(d))

    try:
        settings = load_settings()
        app.state.settings = settings
        logger.info(f"配置完成: model={settings.milm_model}")
    except ValueError as e:
        logger.error(f"配置加载失败: {e}")

    yield
    logger.info("novel2script API 关闭")


app = FastAPI(
    title="Novel2Script API",
    description="中文网络小说 → LRM 剧本转换工具，支持上传/粘贴文本，一键生成 YAML 剧本",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS（允许前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(router, prefix="/api/v1")

# 静态文件：输出目录可直接访问
ensure_dir(Path("output"))
app.mount("/output", StaticFiles(directory="output"), name="output")


@app.get("/")
async def root():
    """健康检查。"""
    return {
        "service": "novel2script",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
    }
