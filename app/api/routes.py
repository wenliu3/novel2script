"""API 路由定义。

提供 RESTful API 接口用于触发转换任务和查询状态。
"""

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.agents.orchestrator import Orchestrator
from app.services.config import load_settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ── 请求/响应模型 ──


class ConvertRequest(BaseModel):
    """转换请求。"""

    novel_dir: str = Field(..., description="小说目录路径")
    chapters: list[int] | None = Field(None, description="指定章节编号列表，None 为全部")


class ConvertResponse(BaseModel):
    """转换响应。"""

    status: str = Field(..., description="任务状态")
    message: str = Field("", description="状态消息")
    novel_name: str = Field("", description="小说名称")
    total_chapters: int = Field(0, description="处理章节数")
    total_scenes: int = Field(0, description="生成场景数")
    total_shots: int = Field(0, description="生成镜头数")
    output_path: str = Field("", description="输出文件路径")


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str
    model: str


# ── 路由 ──


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """检查服务健康状态和 LLM 连接。"""
    try:
        settings = load_settings()
        return HealthResponse(status="ok", model=settings.milm_model)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert", response_model=ConvertResponse)
async def convert_novel(request: ConvertRequest, background_tasks: BackgroundTasks):
    """触发小说转换任务。

    将指定小说目录中的中文章节转换为 LRM 脚本（YAML 格式）。
    任务在后台执行，返回任务状态。
    """
    novel_dir = Path(request.novel_dir)
    if not novel_dir.exists():
        raise HTTPException(status_code=404, detail=f"小说目录不存在: {novel_dir}")

    try:
        settings = load_settings()
        orchestrator = Orchestrator(settings)

        # 同步执行（小规模）或后台执行（大规模）
        script = orchestrator.run(novel_dir=novel_dir, chapters=request.chapters)

        return ConvertResponse(
            status="completed",
            message="转换完成",
            novel_name=novel_dir.name,
            total_chapters=len(script.chapters),
            total_scenes=script.total_scenes(),
            total_shots=script.total_shots(),
            output_path=str(settings.output_base / novel_dir.name),
        )
    except Exception as e:
        logger.error(f"转换失败: {e}")
        raise HTTPException(status_code=500, detail=f"转换失败: {e}")


@router.get("/novels")
async def list_novels():
    """列出 novels/ 目录下所有可用的小说。"""
    novels_dir = Path("novels")
    if not novels_dir.exists():
        return {"novels": []}

    novels = []
    for d in sorted(novels_dir.iterdir()):
        if d.is_dir() and (d / "origin").exists():
            chapter_count = len(list((d / "origin").glob("*.txt")))
            novels.append({
                "name": d.name,
                "chapters": chapter_count,
                "has_character": (d / "character.md").exists(),
                "has_overview": (d / "overview.md").exists(),
            })

    return {"novels": novels}
