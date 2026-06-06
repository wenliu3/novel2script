"""流水线引擎。

核心编排器，负责：
- 按拓扑顺序执行步骤
- 管理步骤间数据传递（上下文）
- 依赖检查与跳过策略
- 重试与超时处理
- 进度跟踪与回调通知
- 并行章节处理（可选）
"""

from __future__ import annotations

import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.workflow.step import Step, StepResult, StepStatus, StepType
from app.workflow.callbacks import CallbackManager, PipelineEvent

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """流水线上下文。

    所有步骤共享的数据容器。
    每个步骤通过 step_id 向上下文写入数据，
    后续步骤通过依赖的 step_id 读取前置数据。

    Usage:
        ctx = PipelineContext()
        ctx.set("chapters", chapter_list)
        chapters = ctx.get("chapters")
    """

    _data: dict[str, Any] = field(default_factory=dict)
    _errors: dict[str, str] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        """存储数据。"""
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """读取数据。"""
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._data

    def set_error(self, key: str, error: str) -> None:
        self._errors[key] = error

    def get_error(self, key: str) -> str:
        return self._errors.get(key, "")

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


@dataclass
class PipelineStats:
    """流水线统计。"""

    total_steps: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    total_retries: int = 0
    total_elapsed: float = 0.0
    step_times: dict[str, float] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return self.completed / self.total_steps

    def summary(self) -> str:
        return (
            f"步骤: {self.completed}/{self.total_steps} 完成, "
            f"{self.failed} 失败, {self.skipped} 跳过, "
            f"重试 {self.total_retries} 次, "
            f"耗时 {self.total_elapsed:.1f}s"
        )


class Pipeline:
    """流水线引擎。

    管理 Step 列表的执行，支持：
    - 拓扑排序（自动解析依赖）
    - 上下文数据传递
    - 重试与超时
    - 回调通知
    - 章节级并行处理

    Usage:
        pipeline = Pipeline(name="novel2script")
        pipeline.add_step(Step(step_id="parse", name="解析章节", fn=parse_fn))
        pipeline.add_step(Step(step_id="analyze", name="分析角色", fn=analyze_fn, depends_on=["parse"]))
        result = pipeline.run(ctx)
    """

    def __init__(self, name: str = "pipeline", max_workers: int = 4) -> None:
        self.name = name
        self.steps: list[Step] = []
        self.context = PipelineContext()
        self.stats = PipelineStats()
        self.callbacks = CallbackManager()
        self.max_workers = max_workers
        self._step_map: dict[str, Step] = {}

    def add_step(self, step: Step) -> "Pipeline":
        """添加步骤（链式调用）。"""
        self.steps.append(step)
        self._step_map[step.step_id] = step
        return self

    def remove_step(self, step_id: str) -> "Pipeline":
        """移除步骤。"""
        self.steps = [s for s in self.steps if s.step_id != step_id]
        self._step_map.pop(step_id, None)
        return self

    def get_step(self, step_id: str) -> Step | None:
        return self._step_map.get(step_id)

    def on(self, event_type: str, callback) -> "Pipeline":
        """注册回调（链式调用）。"""
        self.callbacks.on(event_type, callback)
        return self

    def run(self, ctx: PipelineContext | None = None) -> PipelineStats:
        """执行流水线。

        Args:
            ctx: 外部上下文（可选，为 None 时使用内部上下文）。

        Returns:
            执行统计。
        """
        if ctx:
            self.context = ctx

        start_time = time.time()
        self.stats = PipelineStats(total_steps=len(self.steps))

        # 通知流水线开始
        self.callbacks.emit(PipelineEvent(
            event_type="pipeline_start",
            data=self.name,
            metadata={"total_steps": len(self.steps)},
        ))

        logger.info(f"{'='*50}")
        logger.info(f"🚀 流水线 [{self.name}] 开始: {len(self.steps)} 个步骤")
        logger.info(f"{'='*50}")

        try:
            self._execute_steps()
        except Exception as e:
            logger.error(f"流水线异常: {e}")
            self.callbacks.emit(PipelineEvent(
                event_type="pipeline_error",
                data=str(e),
            ))

        # 计算统计（无论成功失败都更新）
        self.stats.total_elapsed = time.time() - start_time
        self.stats.completed = sum(
            1 for s in self.steps if s.status == StepStatus.COMPLETED
        )
        self.stats.failed = sum(
            1 for s in self.steps if s.status == StepStatus.FAILED
        )
        self.stats.skipped = sum(
            1 for s in self.steps if s.status == StepStatus.SKIPPED
        )

        # 通知流水线完成
        self.callbacks.emit(PipelineEvent(
            event_type="pipeline_complete",
            elapsed_seconds=self.stats.total_elapsed,
            metadata={"stats": self.stats},
        ))

        logger.info(f"{'='*50}")
        logger.info(f"✅ 流水线完成: {self.stats.summary()}")
        logger.info(f"{'='*50}")

        return self.stats

    def reset(self) -> None:
        """重置所有步骤状态。"""
        for step in self.steps:
            step.reset()
        self.context = PipelineContext()
        self.stats = PipelineStats()

    # ──────────────────────────────────────────────
    # 内部执行逻辑
    # ──────────────────────────────────────────────

    def _execute_steps(self) -> None:
        """按拓扑顺序执行步骤。"""
        execution_order = self._topological_sort()
        pipeline_failed = False

        for i, step in enumerate(execution_order):
            # 流水线已失败，后续步骤全部跳过
            if pipeline_failed:
                step.mark_skipped(reason="前置步骤失败")
                self.stats.skipped += 1
                self._emit_progress(i + 1)
                continue

            # 检查依赖
            if not self._check_dependencies(step):
                step.mark_skipped(reason="前置依赖未满足")
                self.stats.skipped += 1
                self._emit_progress(i + 1)
                continue

            # 执行（含重试）
            success = self._execute_with_retry(step)

            if not success:
                pipeline_failed = True

            # 通知进度
            self._emit_progress(i + 1)

    def _execute_with_retry(self, step: Step) -> bool:
        """执行步骤，失败时自动重试。

        Returns:
            True 表示成功或可选步骤失败后跳过，False 表示必需步骤失败。
        """
        while True:
            # 通知步骤开始
            self.callbacks.emit(PipelineEvent(
                event_type="step_start",
                step_id=step.step_id,
                step_name=step.name,
            ))

            step.mark_running()

            try:
                # 执行步骤函数
                if step.fn is None:
                    raise ValueError(f"步骤 {step.step_id} 没有执行函数")

                result_data = step.fn(self.context)

                # 成功
                step.mark_completed(data=result_data)
                self.context.set(step.step_id, result_data)

                self.callbacks.emit(PipelineEvent(
                    event_type="step_complete",
                    step_id=step.step_id,
                    step_name=step.name,
                    elapsed_seconds=step.result.elapsed_seconds,
                ))

                logger.info(f"✓ {step.name} 完成 ({step.result.elapsed_seconds:.1f}s)")
                return True

            except Exception as e:
                error_msg = str(e)
                step.mark_failed(error_msg)
                self.context.set_error(step.step_id, error_msg)

                self.callbacks.emit(PipelineEvent(
                    event_type="step_fail",
                    step_id=step.step_id,
                    step_name=step.name,
                    data=error_msg,
                ))

                # 尝试重试
                if step.can_retry():
                    step.increment_retry()
                    self.stats.total_retries += 1

                    self.callbacks.emit(PipelineEvent(
                        event_type="step_retry",
                        step_id=step.step_id,
                        step_name=step.name,
                        metadata={"retry_count": step.result.retry_count},
                    ))

                    logger.warning(
                        f"↻ {step.name} 失败，重试第 {step.result.retry_count} 次: {error_msg}"
                    )
                    continue

                # 不可重试或重试耗尽
                if step.optional:
                    logger.warning(f"⚠ {step.name} 失败（可选步骤，继续执行）: {error_msg}")
                    step.mark_skipped(reason=f"失败后跳过: {error_msg}")
                    self.stats.skipped += 1
                    return True
                else:
                    logger.error(f"✗ {step.name} 失败（必需步骤，终止流水线）: {error_msg}")
                    return False

    def _check_dependencies(self, step: Step) -> bool:
        """检查步骤的前置依赖是否全部满足。"""
        for dep_id in step.depends_on:
            dep_step = self._step_map.get(dep_id)
            if dep_step is None:
                logger.warning(f"步骤 {step.step_id} 依赖的步骤 {dep_id} 不存在")
                return False
            if dep_step.status != StepStatus.COMPLETED:
                return False
        return True

    def _topological_sort(self) -> list[Step]:
        """拓扑排序：按依赖关系确定执行顺序。"""
        visited: set[str] = set()
        order: list[Step] = []

        def dfs(step: Step) -> None:
            if step.step_id in visited:
                return
            visited.add(step.step_id)
            for dep_id in step.depends_on:
                dep = self._step_map.get(dep_id)
                if dep:
                    dfs(dep)
            order.append(step)

        for step in self.steps:
            dfs(step)

        return order

    def _emit_progress(self, completed: int) -> None:
        """通知进度更新。"""
        self.callbacks.emit(PipelineEvent(
            event_type="progress",
            data=f"{completed}/{len(self.steps)}",
            metadata={
                "completed": completed,
                "total": len(self.steps),
            },
        ))


# ──────────────────────────────────────────────
# 预定义流水线模板
# ──────────────────────────────────────────────


def create_novel_pipeline(
    chapter_agent=None,
    character_agent=None,
    scene_agent=None,
    dialogue_agent=None,
    yaml_builder=None,
    validator=None,
    settings=None,
) -> Pipeline:
    """创建标准的小说转换流水线。

    所有 Agent 传入 None 时创建空壳步骤（用于测试或延迟初始化）。
    """
    pipeline = Pipeline(name="novel2script", max_workers=1)

    # Step 1: 解析章节
    def step_parse(ctx: PipelineContext):
        if chapter_agent and "novel_dir" in ctx.to_dict():
            return chapter_agent.run(novel_dir=ctx.get("novel_dir"))
        return ctx.get("chapters", [])

    pipeline.add_step(Step(
        step_id="parse",
        name="解析章节",
        step_type=StepType.PARSE,
        fn=step_parse,
        description="扫描小说目录，读取并解析章节目录",
    ))

    # Step 2: 章节分析
    def step_analyze(ctx: PipelineContext):
        chapters = ctx.get("parse", [])
        if chapter_agent and chapters:
            return chapter_agent.analyze_chapters(chapters)
        return None

    pipeline.add_step(Step(
        step_id="analyze",
        name="章节分析",
        step_type=StepType.ANALYZE,
        fn=step_analyze,
        depends_on=["parse"],
        description="LLM 深度分析章节摘要、关键事件、地点",
    ))

    # Step 3: 角色提取
    def step_characters(ctx: PipelineContext):
        chapters = ctx.get("parse", [])
        if character_agent and chapters:
            return character_agent.run(chapters_text="", chapters=chapters)
        return None

    pipeline.add_step(Step(
        step_id="characters",
        name="角色提取",
        step_type=StepType.EXTRACT,
        fn=step_characters,
        depends_on=["parse"],
        description="逐章提取角色信息，构建关系图谱",
    ))

    # Step 4-5: 逐章场景+对话（并行章节）
    def step_scenes_and_dialogue(ctx: PipelineContext):
        chapters = ctx.get("parse", [])
        characters = ctx.get("characters")
        analysis = ctx.get("analyze")
        char_list = characters.character_list if characters else None
        char_names = [c.name for c in char_list.characters] if char_list else []

        chapter_scripts = []
        for ch in chapters:
            ch_analysis = None
            if analysis and hasattr(analysis, "analyses"):
                for a in analysis.analyses:
                    if a.chapter_number == ch.number:
                        ch_analysis = a
                        break

            # 场景规划
            scenes = []
            if scene_agent:
                scenes = scene_agent.run(
                    chapter_text=ch.raw_text,
                    chapter_number=ch.number,
                    character_names=char_names,
                    chapter_summary=ch_analysis.summary if ch_analysis else "",
                    location_hints=ch_analysis.location_hints if ch_analysis else [],
                )

            # 对话翻译
            if dialogue_agent:
                for i, scene in enumerate(scenes):
                    scenes[i] = dialogue_agent.run(
                        scene=scene,
                        chapter_text=ch.raw_text,
                        chapter_number=ch.number,
                        character_names=char_names,
                    )

            chapter_scripts.append((ch.number, ch.title, scenes))

        return chapter_scripts

    pipeline.add_step(Step(
        step_id="scenes_dialogue",
        name="场景规划 + 对话翻译",
        step_type=StepType.PLAN,
        fn=step_scenes_and_dialogue,
        depends_on=["parse", "analyze", "characters"],
        description="逐章拆分场景、生成镜头、翻译对话",
    ))

    # Step 6: 组装 YAML
    def step_build(ctx: PipelineContext):
        scripts = ctx.get("scenes_dialogue", [])
        novel_name = ctx.get("novel_name", "unknown")
        if yaml_builder and scripts:
            return yaml_builder.run(novel_name=novel_name, chapter_scripts=scripts)
        return None

    pipeline.add_step(Step(
        step_id="build",
        name="组装 YAML",
        step_type=StepType.BUILD,
        fn=step_build,
        depends_on=["scenes_dialogue"],
        description="将所有 Agent 输出组装为 Script 数据结构",
    ))

    # Step 7: 校验
    def step_validate(ctx: PipelineContext):
        script = ctx.get("build")
        if validator and script:
            return validator.run(script=script)
        return None

    pipeline.add_step(Step(
        step_id="validate",
        name="校验",
        step_type=StepType.VALIDATE,
        fn=step_validate,
        depends_on=["build"],
        optional=True,
        description="校验脚本结构完整性和内容一致性",
    ))

    # Step 8: 导出
    def step_export(ctx: PipelineContext):
        script = ctx.get("build")
        from app.exporters.yaml_exporter import export_yaml
        if script and settings:
            output_path = settings.output_base / ctx.get("novel_name", "output")
            export_yaml(script, output_path, f"{ctx.get('novel_name', 'script')}_script.yaml")
            return output_path
        return None

    pipeline.add_step(Step(
        step_id="export",
        name="导出 YAML",
        step_type=StepType.EXPORT,
        fn=step_export,
        depends_on=["build"],
        description="导出最终的 YAML 脚本文件",
    ))

    return pipeline
