"""FastAPI API 路由。

4 个端点：
- POST /api/upload       → 上传小说文件
- POST /api/convert      → 触发转换（后台运行）
- GET  /api/status/{id}  → 查询任务状态
- GET  /api/download/{n} → 下载 YAML
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_BASE = Path("uploads")
OUTPUT_BASE = Path("output")
_task_store: dict[str, dict[str, Any]] = {}
_MAX_TASKS = 200  # 最多保留的任务数


def _cleanup_tasks():
    """清理旧任务，保留最近 _MAX_TASKS 个。"""
    if len(_task_store) > _MAX_TASKS:
        keys = list(_task_store.keys())
        for k in keys[: len(keys) - _MAX_TASKS]:
            _task_store.pop(k, None)


def _sanitize_name(name: str) -> str:
    """清理小说名，防止路径遍历攻击。"""
    name = name.strip()
    if ".." in name or "/" in name or "\\" in name:
        raise ValueError("无效的小说名称")
    name = re.sub(r"[^\w一-鿿\-]", "_", name)
    name = name.strip("_.")
    if not name or name.startswith("."):
        raise ValueError("无效的小说名称")
    return name


# ── 数据模型 ──

class UploadResponse(BaseModel):
    novel_name: str
    file_count: int
    total_chars: int
    message: str


class ConvertRequest(BaseModel):
    novel_name: str = Field(..., description="小说名称（上传时返回的）")


class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending / processing / completed / failed
    progress: str = ""
    message: str = ""


# ── 端点 ──

@router.post("/upload", response_model=UploadResponse)
async def upload_novel(
    files: list[UploadFile] = File(..., description="小说文件（TXT）"),
    novel_name: str = Form("", description="小说名，留空则自动生成"),
):
    """上传小说文件。"""
    if not files:
        raise HTTPException(400, "请上传至少一个文件")
    if not novel_name:
        novel_name = f"novel_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    else:
        try:
            novel_name = _sanitize_name(novel_name)
        except ValueError:
            raise HTTPException(400, "无效的小说名称")

    upload_dir = UPLOAD_BASE / novel_name / "origin"
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved, total_chars = 0, 0
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
                raise HTTPException(400, f"无法解码: {file.filename}")
        dest = upload_dir / Path(file.filename).name
        dest.write_text(text, encoding="utf-8")
        saved += 1
        total_chars += len(text)

    return UploadResponse(
        novel_name=novel_name,
        file_count=saved,
        total_chars=total_chars,
        message=f"上传成功: {saved} 个文件, {total_chars:,} 字符",
    )


@router.post("/convert")
async def convert_novel(request: ConvertRequest, background_tasks: BackgroundTasks):
    """触发小说转换（后台运行，支持断点续传）。"""
    try:
        safe_name = _sanitize_name(request.novel_name)
    except ValueError:
        raise HTTPException(400, "无效的小说名称")
    novel_dir = UPLOAD_BASE / safe_name
    if not novel_dir.exists():
        raise HTTPException(404, f"小说不存在: {safe_name}，请先上传")

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    _cleanup_tasks()
    _task_store[task_id] = {
        "task_id": task_id, "status": "pending", "message": "任务已提交",
        "novel_name": safe_name,
    }
    background_tasks.add_task(_run_conversion, task_id, safe_name)
    return {"task_id": task_id, "status": "pending", "message": "任务已提交"}


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_status(task_id: str):
    """查询任务状态。"""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(404, f"任务不存在: {task_id}")
    return TaskStatus(**{k: task.get(k, "") for k in TaskStatus.model_fields})


@router.get("/download/{novel_name}")
async def download_yaml(novel_name: str):
    """下载 YAML 文件。"""
    try:
        safe_name = _sanitize_name(novel_name)
    except ValueError:
        raise HTTPException(400, "无效的小说名称")
    path = OUTPUT_BASE / safe_name / f"{safe_name}_script.yaml"
    if not path.exists():
        raise HTTPException(404, f"文件不存在: {safe_name}")
    return FileResponse(str(path), filename=f"{safe_name}_script.yaml", media_type="application/x-yaml")


# ── 后台任务 ──

def _run_conversion(task_id: str, novel_name: str) -> None:
    """后台执行转换（使用新 pipeline，支持断点续传）。"""
    try:
        _task_store[task_id]["status"] = "processing"
        _task_store[task_id]["message"] = "正在读取文件..."

        from app.config import load_settings
        from app.llm import LLM
        from app.core.pipeline import run_pipeline_with_status

        settings = load_settings()
        llm = LLM(
            api_key=settings.milm_api_key,
            base_url=settings.milm_base_url,
            model=settings.milm_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

        # 找到小说文件
        novel_dir = UPLOAD_BASE / novel_name
        origin_dir = novel_dir / "origin"
        txt_files = sorted(origin_dir.glob("*.txt"))
        if not txt_files:
            raise FileNotFoundError("没有 .txt 文件")

        # 如果多个文件，合并为一个
        if len(txt_files) == 1:
            input_path = str(txt_files[0])
        else:
            from app.core.splitter import read_file, clean_text
            parts = []
            for f in txt_files:
                try:
                    _, t = read_file(f)
                    parts.append(t)
                except Exception as e:
                    logger.warning(f"读取文件失败，跳过: {f.name} - {e}")
            merged_text = clean_text("\n\n".join(parts))
            merged_path = origin_dir / f"{novel_name}_merged.txt"
            merged_path.write_text(merged_text, encoding="utf-8")
            input_path = str(merged_path)

        output_path = str(OUTPUT_BASE / novel_name / f"{novel_name}_script.yaml")

        # 执行流水线
        run_pipeline_with_status(
            input_path=input_path,
            output_path=output_path,
            llm=llm,
            novel_name=novel_name,
            chunk_size=settings.chunk_size,
            status_store=_task_store,
            task_id=task_id,
        )

        _task_store[task_id].update({
            "status": "completed",
            "message": f"转换完成，输出: {output_path}",
        })

    except Exception as e:
        logger.error(f"任务 {task_id} 失败: {e}")
        _task_store[task_id].update({"status": "failed", "message": str(e)})
