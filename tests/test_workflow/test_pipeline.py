"""Agent 工作流编排测试。

测试流水线引擎、步骤状态管理、依赖排序、重试机制、回调系统等。
"""

import time
import pytest
from app.workflow.step import Step, StepResult, StepStatus, StepType
from app.workflow.pipeline import Pipeline, PipelineContext, PipelineStats, create_novel_pipeline
from app.workflow.callbacks import CallbackManager, PipelineEvent, logging_callback


# ──────────────────────────────────────
# Step 步骤模型测试
# ──────────────────────────────────────


class TestStep:
    """Step 数据模型测试。"""

    def test_create_step(self):
        s = Step(step_id="s1", name="Test Step")
        assert s.step_id == "s1"
        assert s.status == StepStatus.PENDING

    def test_mark_running(self):
        s = Step(step_id="s1", name="Test")
        s.mark_running()
        assert s.status == StepStatus.RUNNING

    def test_mark_completed(self):
        s = Step(step_id="s1", name="Test")
        s.mark_running()
        result = s.mark_completed(data="output")
        assert s.status == StepStatus.COMPLETED
        assert result.data == "output"
        assert result.is_success

    def test_mark_failed(self):
        s = Step(step_id="s1", name="Test")
        s.mark_running()
        result = s.mark_failed("error msg")
        assert s.status == StepStatus.FAILED
        assert result.error == "error msg"
        assert result.is_failure

    def test_mark_skipped(self):
        s = Step(step_id="s1", name="Test")
        s.mark_skipped("not needed")
        assert s.status == StepStatus.SKIPPED

    def test_can_retry(self):
        s = Step(step_id="s1", name="Test", max_retries=2)
        s.result = StepResult(step_id="s1", status=StepStatus.FAILED, retry_count=0)
        assert s.can_retry() is True
        s.result.retry_count = 1
        assert s.can_retry() is True
        s.result.retry_count = 2
        assert s.can_retry() is False

    def test_increment_retry(self):
        s = Step(step_id="s1", name="Test", max_retries=3)
        s.result = StepResult(step_id="s1", status=StepStatus.FAILED, retry_count=0)
        s.increment_retry()
        assert s.result.retry_count == 1
        assert s.status == StepStatus.PENDING

    def test_reset(self):
        s = Step(step_id="s1", name="Test")
        s.mark_running()
        s.mark_completed(data="x")
        s.reset()
        assert s.status == StepStatus.PENDING
        assert s.result is None

    def test_optional_step(self):
        s = Step(step_id="s1", name="Test", optional=True)
        assert s.optional is True


# ──────────────────────────────────────
# PipelineContext 上下文测试
# ──────────────────────────────────────


class TestPipelineContext:
    """上下文数据容器测试。"""

    def test_set_get(self):
        ctx = PipelineContext()
        ctx.set("key", "value")
        assert ctx.get("key") == "value"

    def test_get_default(self):
        ctx = PipelineContext()
        assert ctx.get("missing", "default") == "default"

    def test_has(self):
        ctx = PipelineContext()
        assert ctx.has("key") is False
        ctx.set("key", 1)
        assert ctx.has("key") is True

    def test_errors(self):
        ctx = PipelineContext()
        ctx.set_error("s1", "something went wrong")
        assert ctx.get_error("s1") == "something went wrong"

    def test_keys(self):
        ctx = PipelineContext()
        ctx.set("a", 1)
        ctx.set("b", 2)
        assert sorted(ctx.keys()) == ["a", "b"]


# ──────────────────────────────────────
# Pipeline 流水线引擎测试
# ──────────────────────────────────────


class TestPipeline:
    """流水线引擎核心测试。"""

    def test_simple_pipeline(self):
        """简单顺序流水线。"""
        p = Pipeline("test")
        p.add_step(Step(step_id="s1", name="Step 1", fn=lambda ctx: "result1"))
        p.add_step(Step(step_id="s2", name="Step 2", fn=lambda ctx: "result2"))

        stats = p.run()
        assert stats.completed == 2
        assert stats.failed == 0
        assert p.context.get("s1") == "result1"
        assert p.context.get("s2") == "result2"

    def test_dependency_order(self):
        """依赖关系应保证执行顺序。"""
        execution_order = []

        def make_fn(step_id):
            def fn(ctx):
                execution_order.append(step_id)
                return step_id
            return fn

        p = Pipeline("test")
        p.add_step(Step(step_id="c", name="C", fn=make_fn("c"), depends_on=["a"]))
        p.add_step(Step(step_id="a", name="A", fn=make_fn("a")))
        p.add_step(Step(step_id="b", name="B", fn=make_fn("b"), depends_on=["a"]))

        p.run()
        # a 必须在 b 和 c 之前
        assert execution_order.index("a") < execution_order.index("b")
        assert execution_order.index("a") < execution_order.index("c")

    def test_context_data_flow(self):
        """步骤间数据应通过上下文传递。"""
        def step1(ctx):
            return [1, 2, 3]

        def step2(ctx):
            data = ctx.get("s1")
            return [x * 2 for x in data]

        p = Pipeline("test")
        p.add_step(Step(step_id="s1", name="Step 1", fn=step1))
        p.add_step(Step(step_id="s2", name="Step 2", fn=step2, depends_on=["s1"]))

        p.run()
        assert p.context.get("s2") == [2, 4, 6]

    def test_failure_stops_pipeline(self):
        """非可选步骤失败应终止流水线。"""
        def fail_fn(ctx):
            raise ValueError("boom")

        p = Pipeline("test")
        p.add_step(Step(step_id="s1", name="Fail", fn=fail_fn))
        p.add_step(Step(step_id="s2", name="Never", fn=lambda ctx: "x"))

        stats = p.run()
        assert stats.failed == 1
        # 后续步骤被标记为 SKIPPED（流水线已终止）
        assert p.get_step("s2").status == StepStatus.SKIPPED

    def test_optional_step_failure(self):
        """可选步骤失败不应阻塞后续步骤。"""
        def fail_fn(ctx):
            raise ValueError("optional fail")

        p = Pipeline("test")
        p.add_step(Step(step_id="s1", name="Optional", fn=fail_fn, optional=True))
        p.add_step(Step(step_id="s2", name="Continue", fn=lambda ctx: "ok"))

        stats = p.run()
        assert stats.skipped == 1
        assert stats.completed == 1
        assert p.context.get("s2") == "ok"

    def test_retry_on_failure(self):
        """失败步骤应自动重试。"""
        attempt = {"count": 0}

        def flaky_fn(ctx):
            attempt["count"] += 1
            if attempt["count"] < 3:
                raise ValueError(f"fail attempt {attempt['count']}")
            return "success"

        p = Pipeline("test")
        p.add_step(Step(step_id="s1", name="Flaky", fn=flaky_fn, max_retries=3))

        stats = p.run()
        assert stats.completed == 1
        assert stats.total_retries >= 2
        assert p.context.get("s1") == "success"

    def test_retry_exhausted(self):
        """重试耗尽后应标记失败。"""
        def always_fail(ctx):
            raise ValueError("always fail")

        p = Pipeline("test")
        p.add_step(Step(step_id="s1", name="Fail", fn=always_fail, max_retries=1, optional=True))

        stats = p.run()
        assert stats.skipped == 1  # optional 失败后跳过

    def test_skipped_dependency(self):
        """依赖步骤失败/跳过时，后续步骤应被跳过。"""
        def fail_fn(ctx):
            raise ValueError("fail")

        p = Pipeline("test")
        p.add_step(Step(step_id="s1", name="Fail", fn=fail_fn))
        p.add_step(Step(step_id="s2", name="Depend", fn=lambda ctx: "x", depends_on=["s1"]))

        stats = p.run()
        assert p.get_step("s2").status == StepStatus.SKIPPED

    def test_reset(self):
        """重置应清除所有步骤状态。"""
        p = Pipeline("test")
        p.add_step(Step(step_id="s1", name="S1", fn=lambda ctx: "x"))
        p.run()
        assert p.get_step("s1").status == StepStatus.COMPLETED

        p.reset()
        assert p.get_step("s1").status == StepStatus.PENDING

    def test_pipeline_stats(self):
        """统计信息应正确计算。"""
        p = Pipeline("test")
        p.add_step(Step(step_id="s1", name="S1", fn=lambda ctx: "a"))
        p.add_step(Step(step_id="s2", name="S2", fn=lambda ctx: "b"))

        stats = p.run()
        assert stats.total_steps == 2
        assert stats.completed == 2
        assert stats.success_rate == 1.0


# ──────────────────────────────────────
# CallbackManager 回调系统测试
# ──────────────────────────────────────


class TestCallbackManager:
    """回调管理器测试。"""

    def test_register_and_emit(self):
        events = []
        mgr = CallbackManager()
        mgr.on("test", lambda e: events.append(e.event_type))
        mgr.emit(PipelineEvent(event_type="test"))
        assert events == ["test"]

    def test_multiple_callbacks(self):
        results = []
        mgr = CallbackManager()
        mgr.on("event", lambda e: results.append("a"))
        mgr.on("event", lambda e: results.append("b"))
        mgr.emit(PipelineEvent(event_type="event"))
        assert results == ["a", "b"]

    def test_off_removes_callback(self):
        results = []
        handler = lambda e: results.append("x")
        mgr = CallbackManager()
        mgr.on("event", handler)
        mgr.off("event", handler)
        mgr.emit(PipelineEvent(event_type="event"))
        assert results == []

    def test_exception_safety(self):
        """回调异常不应影响其他回调。"""
        results = []
        mgr = CallbackManager()
        mgr.on("event", lambda e: 1 / 0)  # 会抛异常
        mgr.on("event", lambda e: results.append("ok"))
        mgr.emit(PipelineEvent(event_type="event"))
        assert results == ["ok"]

    def test_clear(self):
        mgr = CallbackManager()
        mgr.on("a", lambda e: None)
        mgr.on("b", lambda e: None)
        mgr.clear()
        assert mgr._callbacks == {}


# ──────────────────────────────────────
# Pipeline 与 Callback 集成测试
# ──────────────────────────────────────


class TestPipelineCallbacks:
    """流水线回调集成测试。"""

    def test_pipeline_events(self):
        events = []
        mgr = CallbackManager()
        mgr.on("pipeline_start", lambda e: events.append("start"))
        mgr.on("step_start", lambda e: events.append(f"step_start:{e.step_id}"))
        mgr.on("step_complete", lambda e: events.append(f"step_done:{e.step_id}"))
        mgr.on("pipeline_complete", lambda e: events.append("complete"))

        p = Pipeline("test")
        p.callbacks = mgr
        p.add_step(Step(step_id="s1", name="S1", fn=lambda ctx: "ok"))

        p.run()
        assert "start" in events
        assert "step_start:s1" in events
        assert "step_done:s1" in events
        assert "complete" in events

    def test_progress_events(self):
        progress_updates = []

        def on_progress(e):
            progress_updates.append((e.metadata.get("completed", 0), e.metadata.get("total", 0)))

        p = Pipeline("test")
        p.on("progress", on_progress)
        p.add_step(Step(step_id="s1", name="S1", fn=lambda ctx: "a"))
        p.add_step(Step(step_id="s2", name="S2", fn=lambda ctx: "b"))

        p.run()
        assert len(progress_updates) == 2
        assert progress_updates[-1] == (2, 2)


# ──────────────────────────────────────
# create_novel_pipeline 模板测试
# ──────────────────────────────────────


class TestNovelPipelineTemplate:
    """标准流水线模板测试。"""

    def test_template_structure(self):
        """模板应包含所有必需步骤。"""
        pipeline = create_novel_pipeline()
        step_ids = [s.step_id for s in pipeline.steps]
        assert "parse" in step_ids
        assert "analyze" in step_ids
        assert "characters" in step_ids
        assert "scenes_dialogue" in step_ids
        assert "build" in step_ids
        assert "validate" in step_ids
        assert "export" in step_ids

    def test_template_dependencies(self):
        """模板依赖关系应正确。"""
        pipeline = create_novel_pipeline()
        build_step = pipeline.get_step("build")
        assert "scenes_dialogue" in build_step.depends_on

        validate_step = pipeline.get_step("validate")
        assert "build" in validate_step.depends_on

    def test_template_runnable(self):
        """模板在无 Agent 时应可执行（空壳模式）。"""
        pipeline = create_novel_pipeline()
        ctx = PipelineContext()
        ctx.set("novel_name", "test")
        stats = pipeline.run(ctx)
        assert stats.completed == len(pipeline.steps)
