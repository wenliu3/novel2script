"""FastAPI 应用入口。

启动 FastAPI 服务，注册路由，管理应用生命周期。
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.services.config import load_settings
from app.utils.logger import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    setup_logging(verbose=False)
    logger.info("novel2script API 启动中...")

    try:
        settings = load_settings()
        app.state.settings = settings
        logger.info(f"配置加载完成: model={settings.milm_model}")
    except ValueError as e:
        logger.error(f"配置加载失败: {e}")
        raise

    yield

    logger.info("novel2script API 关闭")


app = FastAPI(
    title="novel2script API",
    description="中文网络小说到 LRM 脚本的转换工具",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """健康检查。"""
    return {
        "service": "novel2script",
        "version": "0.1.0",
        "status": "running",
    }
