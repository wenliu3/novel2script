"""API 路由定义。

提供 RESTful API 接口：
- 健康检查 + LLM 状态
- 小说文件上传（TXT/MD/DOCX）
- 文本粘贴直接转换
- 触发转换任务（目录/上传/粘贴）
- 任务状态查询
- YAML 下载 + 预览
- 可用小说列表
"""

from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.agents.orchestrator import Orchestrator
from app.parsers.novel_parser import NovelInfo, parse_novel, parse_single_file, parse_text_content
from app.services.config import Settings, load_settings
from app.utils.file_utils import ensure_dir

logger = logging.getLogger(__name__)
router = APIRouter()

# ── 上传根目录 ──
UPLOAD_BASE = Path("uploads")
NOVELS_BASE = Path("novels")

# ── 任务状态存储（内存） ──
_task_store: dict[str, dict[str, Any]] = {}


# ═══════════════════════════════════════════════════════════════
# 请求/响应模型
# ═══════════════════════════════════════════════════════════════


class ConvertRequest(BaseModel):
    """目录转换请求。"""
    novel_dir: str = Field(..., description="小说目录路径")
    chapters: list[int] | None = Field(None, description="指定章节编号")


class TextConvertRequest(BaseModel):
    """文本粘贴转换请求。"""
    text: str = Field(..., description="小说文本内容")
    title: str = Field("未命名小说", description="小说标题")
    genre: str = Field("", description="剧本类型")
    chapters: list[int] | None = Field(None, description="指定章节编号")


class ConvertResponse(BaseModel):
    """转换响应。"""
    task_id: str = Field("", description="任务 ID")
    status: str = Field("processing", description="任务状态")
    message: str = Field("", description="状态消息")
    novel_name: str = Field("", description="小说名称")
    total_chapters: int = Field(0)
    total_scenes: int = Field(0)
    total_beats: int = Field(0)
    total_shots: int = Field(0)
    logline: str = Field("", description="故事梗概")
    output_path: str = Field("", description="YAML 输出路径")
    characters: list[dict] = Field(default_factory=list, description="角色列表")
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    elapsed_seconds: float = Field(0.0)


class TaskStatus(BaseModel):
    """任务状态响应。"""
    task_id: str
    status: str  # pending / processing / completed / failed
    message: str = ""
    result: ConvertResponse | None = None


class UploadResponse(BaseModel):
    """上传响应。"""
    novel_name: str = ""
    file_count: int = 0
    total_chars: int = 0
    message: str = ""


class NovelListItem(BaseModel):
    """小说列表项。"""
    name: str
    chapters: int
    has_character: bool = False
    has_overview: bool = False


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════


def _get_settings() -> Settings:
    """获取配置，带错误处理。"""
    try:
        return load_settings()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"配置错误: {e}")


def _get_orchestrator() -> Orchestrator:
    """获取编排器实例。"""
    return Orchestrator(_get_settings())


def _run_conversion(
    task_id: str,
    novel_dir: Path,
    chapters: list[int] | None = None,
    genre: str = "",
) -> None:
    """后台运行转换任务，结果写入 _task_store。"""
    try:
        _task_store[task_id]["status"] = "processing"
        orchestrator = _get_orchestrator()
        script = orchestrator.run(novel_dir=novel_dir, chapters=chapters)

        chars = [
            {"id": c.id, "name": c.name, "role": c.role}
            for c in script.characters
        ]

        _task_store[task_id].update({
            "status": "completed",
            "message": "转换完成",
            "result": ConvertResponse(
                task_id=task_id,
                status="completed",
                message="转换完成",
                novel_name=script.title,
                total_chapters=script.metadata.total_chapters,
                total_scenes=script.metadata.total_scenes,
                total_beats=script.metadata.total_beats,
                total_shots=script.metadata.total_shots,
                logline=script.logline,
                output_path=str(_get_settings().output_base / novel_dir.name),
                characters=chars,
            ),
        })
    except Exception as e:
        logger.error(f"任务 {task_id} 失败: {e}")
        _task_store[task_id].update({
            "status": "failed",
            "message": str(e),
        })


# ═══════════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════════


@router.get("/health")
async def health():
    """健康检查 + LLM 状态。"""
    try:
        settings = _get_settings()
        return {
            "status": "ok",
            "model": settings.milm_model,
            "version": "0.1.0",
        }
    except HTTPException:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "配置未就绪"},
        )


# ═══════════════════════════════════════════════════════════════
# 文件上传
# ═══════════════════════════════════════════════════════════════


@router.post("/upload", response_model=UploadResponse)
async def upload_novel(
    files: list[UploadFile] = File(..., description="小说文件（TXT/MD）"),
    novel_name: str = Form("", description="小说名，留空则自动生成"),
):
    """上传小说章节文件。

    支持单文件（整本小说）或多文件（每章一个文件）。
    文件保存到 uploads/{novel_name}/origin/ 目录。
    """
    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一个文件")

    # 生成小说名
    if not novel_name:
        novel_name = f"novel_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    upload_dir = UPLOAD_BASE / novel_name / "origin"
    ensure_dir(upload_dir)

    saved = 0
    total_chars = 0
    for file in files:
        if not file.filename:
            continue

        content = await file.read()
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("gbk")
            except Exception:
                raise HTTPException(status_code=400, detail=f"无法解码文件: {file.filename}")

        # 保存文件
        safe_name = Path(file.filename).name
        dest = upload_dir / safe_name
        dest.write_text(text, encoding="utf-8")
        saved += 1
        total_chars += len(text)

    logger.info(f"上传完成: {novel_name}, {saved} 文件, {total_chars} 字符")

    return UploadResponse(
        novel_name=novel_name,
        file_count=saved,
        total_chars=total_chars,
        message=f"上传成功: {saved} 个文件",
    )


# ═══════════════════════════════════════════════════════════════
# 文本粘贴转换
# ═══════════════════════════════════════════════════════════════


@router.post("/convert/text", response_model=ConvertResponse)
async def convert_text(request: TextConvertRequest):
    """直接粘贴文本进行转换。

    适用于小规模文本（< 10万字），同步返回结果。
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="文本内容为空")

    # 保存到临时目录
    novel_name = request.title or f"paste_{uuid.uuid4().hex[:8]}"
    upload_dir = UPLOAD_BASE / novel_name / "origin"
    ensure_dir(upload_dir)

    text_path = upload_dir / "full.txt"
    text_path.write_text(request.text, encoding="utf-8")

    try:
        orchestrator = _get_orchestrator()
        script = orchestrator.run(
            novel_dir=UPLOAD_BASE / novel_name,
            chapters=request.chapters,
        )

        chars = [
            {"id": c.id, "name": c.name, "role": c.role}
            for c in script.characters
        ]

        return ConvertResponse(
            task_id="",
            status="completed",
            message="转换完成",
            novel_name=script.title,
            total_chapters=script.metadata.total_chapters,
            total_scenes=script.metadata.total_scenes,
            total_beats=script.metadata.total_beats,
            total_shots=script.metadata.total_shots,
            logline=script.logline,
            output_path=str(_get_settings().output_base / novel_name),
            characters=chars,
        )
    except Exception as e:
        logger.error(f"文本转换失败: {e}")
        raise HTTPException(status_code=500, detail=f"转换失败: {e}")


# ═══════════════════════════════════════════════════════════════
# 目录/上传小说转换
# ═══════════════════════════════════════════════════════════════


@router.post("/convert", response_model=ConvertResponse)
async def convert_novel(
    request: ConvertRequest,
    background_tasks: BackgroundTasks,
):
    """触发小说转换（目录模式）。

    适合已上传到 uploads/ 或 novels/ 目录的小说。
    大任务在后台执行，返回 task_id 供轮询。
    """
    novel_dir = Path(request.novel_dir)
    if not novel_dir.exists():
        raise HTTPException(status_code=404, detail=f"目录不存在: {novel_dir}")

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    _task_store[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "message": "任务已提交",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    background_tasks.add_task(
        _run_conversion, task_id, novel_dir, request.chapters
    )

    return ConvertResponse(
        task_id=task_id,
        status="pending",
        message="任务已提交，请轮询 /convert/{task_id}/status",
        novel_name=novel_dir.name,
    )


@router.post("/convert/{novel_name}", response_model=ConvertResponse)
async def convert_uploaded_novel(
    novel_name: str,
    background_tasks: BackgroundTasks,
    chapters: list[int] | None = None,
):
    """触发已上传小说的转换。

    小说文件需先通过 POST /upload 上传。
    """
    novel_dir = UPLOAD_BASE / novel_name
    if not novel_dir.exists():
        raise HTTPException(status_code=404, detail=f"小说不存在: {novel_name}，请先上传")

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    _task_store[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "message": "任务已提交",
    }

    background_tasks.add_task(_run_conversion, task_id, novel_dir, chapters)

    return ConvertResponse(
        task_id=task_id,
        status="pending",
        message=f"任务已提交: {task_id}",
        novel_name=novel_name,
    )


# ═══════════════════════════════════════════════════════════════
# 任务状态
# ═══════════════════════════════════════════════════════════════


@router.get("/convert/{task_id}/status", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """查询转换任务状态。"""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return TaskStatus(
        task_id=task_id,
        status=task.get("status", "unknown"),
        message=task.get("message", ""),
        result=task.get("result"),
    )


# ═══════════════════════════════════════════════════════════════
# YAML 下载和预览
# ═══════════════════════════════════════════════════════════════


@router.get("/download/{novel_name}")
async def download_yaml(novel_name: str):
    """下载生成好的 YAML 文件。"""
    # 先检查文件是否存在（不依赖配置）
    output_base = Path("output")
    yaml_path = output_base / novel_name / f"{novel_name}_script.yaml"

    # 也搜索配置中指定的目录
    try:
        settings = _get_settings()
        alt_path = settings.output_base / novel_name / f"{novel_name}_script.yaml"
        if alt_path.exists():
            yaml_path = alt_path
    except Exception:
        pass

    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail=f"YAML 文件不存在: {novel_name}")

    return FileResponse(
        path=str(yaml_path),
        filename=f"{novel_name}_script.yaml",
        media_type="application/x-yaml",
    )


@router.get("/preview/{novel_name}")
async def preview_yaml(novel_name: str):
    """预览 YAML 内容。"""
    output_base = Path("output")
    yaml_path = output_base / novel_name / f"{novel_name}_script.yaml"

    try:
        settings = _get_settings()
        alt_path = settings.output_base / novel_name / f"{novel_name}_script.yaml"
        if alt_path.exists():
            yaml_path = alt_path
    except Exception:
        pass

    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail=f"YAML 文件不存在: {novel_name}")

    content = yaml_path.read_text(encoding="utf-8")
    return {"novel_name": novel_name, "yaml": content}


# ═══════════════════════════════════════════════════════════════
# 小说管理
# ═══════════════════════════════════════════════════════════════


@router.get("/novels")
async def list_novels():
    """列出所有可用的小说（novels/ + uploads/）。"""
    novels: list[dict] = []

    for base in (NOVELS_BASE, UPLOAD_BASE):
        if not base.exists():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir():
                continue
            origin = d / "origin"
            if not origin.exists():
                continue
            chapter_count = len(list(origin.glob("*.txt")))
            novels.append({
                "name": d.name,
                "source": base.name,
                "chapters": chapter_count,
                "has_character": (d / "character.md").exists(),
                "has_overview": (d / "overview.md").exists(),
            })

    return {"novels": novels}


@router.get("/novels/{novel_name}")
async def get_novel_info(novel_name: str):
    """获取指定小说的详细信息。"""
    for base in (NOVELS_BASE, UPLOAD_BASE):
        novel_dir = base / novel_name
        if novel_dir.exists() and (novel_dir / "origin").exists():
            try:
                info = parse_novel(novel_dir)
                return {
                    "name": info.name,
                    "source": base.name,
                    "chapters": info.chapter_count,
                    "total_chars": info.total_chars,
                    "avg_chapter_length": round(info.avg_chapter_length),
                    "parse_mode": info.parse_mode,
                    "has_character": info.has_character_file,
                    "has_overview": info.has_overview_file,
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"解析失败: {e}")

    raise HTTPException(status_code=404, detail=f"小说不存在: {novel_name}")


@router.delete("/novels/{novel_name}")
async def delete_novel(novel_name: str):
    """删除已上传的小说。"""
    for base in (UPLOAD_BASE,):
        novel_dir = base / novel_name
        if novel_dir.exists():
            shutil.rmtree(novel_dir)
            return {"message": f"已删除: {novel_name}"}

    raise HTTPException(status_code=404, detail=f"小说不存在: {novel_name}")
