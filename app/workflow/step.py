"""工作流步骤定义。

定义流水线中每个步骤的数据结构和状态管理。
"""

from __future__ import annotations

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    """步骤执行状态。"""

    PENDING = "pending"          # 等待执行
    RUNNING = "running"          # 正在执行
    COMPLETED = "completed"      # 执行成功
    FAILED = "failed"            # 执行失败
    SKIPPED = "skipped"          # 已跳过
    RETRYING = "retrying"        # 重试中


class StepType(str, Enum):
    """步骤类型。"""

    PARSE = "parse"              # 文件解析
    ANALYZE = "analyze"          # 章节分析
    EXTRACT = "extract"          # 角色提取
    PLAN = "plan"                # 场景规划
    TRANSLATE = "translate"      # 对话翻译
    BUILD = "build"              # 结构组装
    VALIDATE = "validate"        # 校验
    EXPORT = "export"            # 导出输出
    CUSTOM = "custom"            # 自定义步骤


@dataclass
class StepResult:
    """步骤执行结果。"""

    step_id: str
    status: StepStatus
    data: Any = None             # 步骤输出数据
    error: str = ""              # 错误信息
    elapsed_seconds: float = 0.0 # 执行耗时
    retry_count: int = 0         # 已重试次数
    metadata: dict = field(default_factory=dict)  # 附加信息

    @property
    def is_success(self) -> bool:
        return self.status == StepStatus.COMPLETED

    @property
    def is_failure(self) -> bool:
        return self.status == StepStatus.FAILED


@dataclass
class Step:
    """工作流步骤。

    每个步骤封装一个 Agent 的执行逻辑，包含：
    - 执行函数（callable）
    - 依赖的前置步骤 ID
    - 重试策略
    - 超时设置
    - 是否可跳过

    Attributes:
        step_id: 步骤唯一标识。
        name: 步骤显示名称。
        step_type: 步骤类型。
        fn: 执行函数，签名为 fn(context) -> Any。
        depends_on: 前置依赖步骤 ID 列表。
        max_retries: 最大重试次数。
        timeout: 超时时间（秒），0 表示不限。
        optional: 是否可跳过（失败不阻塞后续）。
        description: 步骤描述。
    """

    step_id: str
    name: str
    step_type: StepType = StepType.CUSTOM
    fn: Callable[..., Any] | None = None
    depends_on: list[str] = field(default_factory=list)
    max_retries: int = 2
    timeout: float = 0.0
    optional: bool = False
    description: str = ""

    # 运行时状态
    status: StepStatus = field(default=StepStatus.PENDING, init=False)
    result: StepResult | None = field(default=None, init=False)
    _start_time: float = field(default=0.0, init=False, repr=False)

    def mark_running(self) -> None:
        """标记为执行中。"""
        self.status = StepStatus.RUNNING
        self._start_time = time.time()

    def mark_completed(self, data: Any = None, metadata: dict | None = None) -> StepResult:
        """标记为完成。"""
        elapsed = time.time() - self._start_time if self._start_time else 0
        self.status = StepStatus.COMPLETED
        self.result = StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED,
            data=data,
            elapsed_seconds=elapsed,
            retry_count=self.result.retry_count if self.result else 0,
            metadata=metadata or {},
        )
        return self.result

    def mark_failed(self, error: str) -> StepResult:
        """标记为失败。"""
        elapsed = time.time() - self._start_time if self._start_time else 0
        self.status = StepStatus.FAILED
        self.result = StepResult(
            step_id=self.step_id,
            status=StepStatus.FAILED,
            error=error,
            elapsed_seconds=elapsed,
            retry_count=self.result.retry_count if self.result else 0,
        )
        return self.result

    def mark_skipped(self, reason: str = "") -> StepResult:
        """标记为跳过。"""
        self.status = StepStatus.SKIPPED
        self.result = StepResult(
            step_id=self.step_id,
            status=StepStatus.SKIPPED,
            error=reason,
        )
        return self.result

    def can_retry(self) -> bool:
        """是否还能重试。"""
        current_retries = self.result.retry_count if self.result else 0
        return current_retries < self.max_retries

    def increment_retry(self) -> None:
        """重试计数 +1。"""
        if self.result:
            self.result.retry_count += 1
        else:
            self.result = StepResult(step_id=self.step_id, status=StepStatus.RETRYING, retry_count=1)
        self.status = StepStatus.PENDING  # 重置为待执行

    def reset(self) -> None:
        """重置步骤状态。"""
        self.status = StepStatus.PENDING
        self.result = None
        self._start_time = 0.0
