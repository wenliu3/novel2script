"""工作流回调系统。

支持在流水线的各个生命周期事件中注册回调函数，
用于进度通知、日志记录、外部系统集成等。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from app.workflow.step import Step, StepResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineEvent:
    """流水线事件。"""

    event_type: str             # step_start / step_complete / step_fail / pipeline_start / pipeline_complete / pipeline_error
    step_id: str = ""
    step_name: str = ""
    data: Any = None
    elapsed_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)


# 回调函数类型: (event: PipelineEvent) -> None
PipelineCallback = Callable[[PipelineEvent], None]


class CallbackManager:
    """回调管理器。

    管理流水线生命周期回调：

    - on_pipeline_start: 流水线开始
    - on_pipeline_complete: 流水线完成
    - on_pipeline_error: 流水线出错
    - on_step_start: 步骤开始
    - on_step_complete: 步骤完成
    - on_step_fail: 步骤失败
    - on_step_retry: 步骤重试
    - on_progress: 进度更新（每完成一个步骤）

    Usage:
        manager = CallbackManager()
        manager.on("step_complete", my_handler)
        manager.emit(PipelineEvent(event_type="step_start", step_id="parse"))
    """

    def __init__(self) -> None:
        self._callbacks: dict[str, list[PipelineCallback]] = {}

    def on(self, event_type: str, callback: PipelineCallback) -> None:
        """注册回调。

        Args:
            event_type: 事件类型。
            callback: 回调函数。
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def off(self, event_type: str, callback: PipelineCallback) -> None:
        """取消注册。"""
        if event_type in self._callbacks:
            self._callbacks[event_type] = [
                cb for cb in self._callbacks[event_type] if cb != callback
            ]

    def emit(self, event: PipelineEvent) -> None:
        """触发事件。

        异常安全：单个回调的异常不会影响其他回调。
        """
        callbacks = self._callbacks.get(event.event_type, [])
        for cb in callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.warning(f"回调执行失败 ({event.event_type}): {e}")

    def clear(self) -> None:
        """清除所有回调。"""
        self._callbacks.clear()


# ── 预置回调 ──


def logging_callback(event: PipelineEvent) -> None:
    """日志回调：将事件输出到日志。"""
    if event.event_type == "pipeline_start":
        logger.info(f"🚀 流水线开始: {event.metadata.get('total_steps', 0)} 个步骤")
    elif event.event_type == "pipeline_complete":
        elapsed = event.elapsed_seconds
        logger.info(f"✅ 流水线完成 ({elapsed:.1f}s)")
    elif event.event_type == "pipeline_error":
        logger.error(f"❌ 流水线出错: {event.data}")
    elif event.event_type == "step_start":
        logger.info(f"▶ 开始: {event.step_name}")
    elif event.event_type == "step_complete":
        logger.info(f"✓ 完成: {event.step_name} ({event.elapsed_seconds:.1f}s)")
    elif event.event_type == "step_fail":
        logger.error(f"✗ 失败: {event.step_name} - {event.data}")
    elif event.event_type == "step_retry":
        logger.warning(f"↻ 重试: {event.step_name} (第{event.metadata.get('retry_count', 0)}次)")


def progress_callback(event: PipelineEvent) -> None:
    """进度回调：打印进度条。"""
    if event.event_type in ("step_complete", "step_fail", "step_skipped"):
        completed = event.metadata.get("completed", 0)
        total = event.metadata.get("total", 0)
        if total > 0:
            pct = int(completed / total * 100)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            logger.info(f"进度: [{bar}] {pct}% ({completed}/{total})")
