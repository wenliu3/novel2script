"""场景规划 Agent。

将章节文本拆分为场景，并为每个场景生成详细的视觉规划信息。
支持智能场景拆分、连续性追踪、转场设计、场景验证。
"""

import re
import logging
from pathlib import Path

from app.agents.base_agent import BaseAgent
from app.schema.scene import Scene, ScenePlan
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# 单次 LLM 调用的最大文本长度
CHUNK_SIZE = 10000


class SceneAgent(BaseAgent):
    """场景规划 Agent。

    完整流程：
    1. 分析章节文本，识别场景边界
    2. 为每个场景生成标题、地点、时间、氛围
    3. 标注场景标签（动作戏/对话戏/闪回等）
    4. 设计场景间转场方式
    5. 追踪角色连续性（出场角色、位置、状态）
    6. 计算场景预估时长
    7. 输出完整的 ScenePlan

    Attributes:
        name: Agent 名称。
        llm: LLM 服务实例。
        chunk_size: 单次处理的最大文本长度。
    """

    def __init__(self, llm: LLMService, chunk_size: int = CHUNK_SIZE) -> None:
        super().__init__("scene_agent", llm)
        self.chunk_size = chunk_size

    def execute(
        self,
        chapter_text: str,
        chapter_number: int,
        character_names: list[str] | None = None,
        chapter_summary: str = "",
        location_hints: list[str] | None = None,
    ) -> list[Scene]:
        """将章节拆分为场景。

        Args:
            chapter_text: 章节原文。
            chapter_number: 章节编号。
            character_names: 已知角色名列表。
            chapter_summary: 章节摘要（由 chapter_agent 提供）。
            location_hints: 地点线索（由 chapter_agent 提供）。

        Returns:
            拆分后的场景列表。
        """
        self.logger.info(f"开始场景规划: 第{chapter_number}章 ({len(chapter_text):,} 字符)")

        # ── Step 1: 调用 LLM 拆分场景 ──
        scene_data = self._call_llm_for_scenes(
            chapter_text, chapter_number, character_names, chapter_summary, location_hints
        )

        # ── Step 2: 解析为 Scene 对象 ──
        scenes = self._parse_scenes(scene_data, chapter_number)

        # ── Step 3: 后处理（转场设计、连续性追踪） ──
        scenes = self._post_process(scenes, chapter_number)

        self.logger.info(
            f"场景规划完成: 第{chapter_number}章 → {len(scenes)} 个场景, "
            f"预估总时长 {sum(s.total_duration for s in scenes):.0f}s"
        )

        return scenes

    def execute_full_plan(
        self,
        chapter_text: str,
        chapter_number: int,
        chapter_title: str = "",
        character_names: list[str] | None = None,
        chapter_summary: str = "",
        location_hints: list[str] | None = None,
    ) -> ScenePlan:
        """执行完整场景规划，返回 ScenePlan（含验证结果）。

        Args:
            chapter_text: 章节原文。
            chapter_number: 章节编号。
            chapter_title: 章节标题。
            character_names: 已知角色名列表。
            chapter_summary: 章节摘要。
            location_hints: 地点线索。

        Returns:
            完整的 ScenePlan 对象。
        """
        scenes = self.execute(
            chapter_text, chapter_number, character_names, chapter_summary, location_hints
        )

        plan = ScenePlan(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            scenes=scenes,
            scene_count=len(scenes),
            total_estimated_duration=sum(s.total_duration for s in scenes),
        )

        # 结构校验
        errors = plan.validate_structure()
        if errors:
            for err in errors:
                self.logger.warning(f"  ⚠ {err}")

        return plan

    # ──────────────────────────────────────────────
    # 内部方法
    # ──────────────────────────────────────────────

    def _call_llm_for_scenes(
        self,
        chapter_text: str,
        chapter_number: int,
        character_names: list[str] | None,
        chapter_summary: str,
        location_hints: list[str] | None,
    ) -> dict:
        """调用 LLM 进行场景拆分。"""
        # 构建上下文
        names_context = ""
        if character_names:
            names_context = f"已知角色: {', '.join(character_names)}"

        summary_context = ""
        if chapter_summary:
            summary_context = f"章节摘要: {chapter_summary}"

        location_context = ""
        if location_hints:
            location_context = f"已知地点: {', '.join(location_hints)}"

        # 文本截断（如果过长）
        truncated = chapter_text[:self.chunk_size] if len(chapter_text) > self.chunk_size else chapter_text

        # 构建提示词
        system_prompt = (
            "You are a professional film director and screenwriter specializing in "
            "converting Chinese web novels into visual scripts. "
            "Always respond with valid JSON."
        )

        prompt_template = self.load_prompt("scene_splitting")
        user_prompt = self.render_prompt(
            prompt_template,
            user_content=truncated,
            chapter_number=str(chapter_number),
            character_names=names_context,
            chapter_summary=summary_context,
            location_hints=location_context,
        )

        return self.llm.chat_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

    def _parse_scenes(self, data: dict, chapter_number: int) -> list[Scene]:
        """将 LLM 返回的 JSON 解析为 Scene 对象列表。"""
        scenes = []
        for i, scene_data in enumerate(data.get("scenes", []), 1):
            try:
                scene = Scene(
                    id=f"ch{chapter_number}_s{i}",
                    title=scene_data.get("title", f"Scene {i}"),
                    location=scene_data.get("location", ""),
                    time=scene_data.get("time", ""),
                    mood=scene_data.get("mood", ""),
                    summary=scene_data.get("summary", ""),
                    tags=scene_data.get("tags", []),
                    transition_in=scene_data.get("transition_in", "cut" if i == 1 else "cut"),
                    transition_out=scene_data.get("transition_out", "cut"),
                    estimated_duration=scene_data.get("estimated_duration", 0.0),
                    props=scene_data.get("props", []),
                    characters_present=scene_data.get("characters_present", []),
                    continuity_notes=scene_data.get("continuity_notes", ""),
                )
                scenes.append(scene)
            except Exception as e:
                self.logger.warning(f"跳过场景 {i}: {e}")
                continue

        return scenes

    def _post_process(self, scenes: list[Scene], chapter_number: int) -> list[Scene]:
        """后处理：转场设计、连续性追踪、时长计算。"""
        if not scenes:
            return scenes

        # 第一个场景默认淡入
        if scenes[0].transition_in == "cut":
            scenes[0].transition_in = "fade_in"

        # 最后一个场景默认淡出
        if scenes[-1].transition_out == "cut":
            scenes[-1].transition_out = "fade_out"

        # 如果场景没有预估时长，根据标签和内容推断
        for scene in scenes:
            if scene.estimated_duration <= 0:
                scene.estimated_duration = self._estimate_duration(scene)

        # 连续性追踪：记录角色位置变化
        self._track_continuity(scenes)

        return scenes

    def _estimate_duration(self, scene: Scene) -> float:
        """根据场景特征推断预估时长。

        规则：
        - 动作戏：快节奏，每个镜头约 3-5 秒
        - 对话戏：中等节奏，每个镜头约 5-8 秒
        - 闪回：较短，3-5 秒
        - 旁白叙述：较长，6-10 秒
        - 默认：5 秒/镜头，最少 3 个镜头
        """
        # 基础时长：根据标签
        if "action" in scene.tags:
            base_per_shot = 4.0
        elif "flashback" in scene.tags:
            base_per_shot = 4.0
        elif "narration" in scene.tags:
            base_per_shot = 8.0
        elif "quiet" in scene.tags:
            base_per_shot = 7.0
        else:
            base_per_shot = 5.0

        # 至少 3 个镜头
        shot_count = max(scene.shot_count, 3)
        return shot_count * base_per_shot

    def _track_continuity(self, scenes: list[Scene]) -> None:
        """追踪场景间的角色连续性。

        检查：
        - 上一场景出场的角色是否在下一场景合理出现
        - 角色位置变化是否与转场方式匹配
        """
        prev_characters = set()
        for i, scene in enumerate(scenes):
            if i > 0 and prev_characters:
                # 检查角色连续性
                current_chars = set(scene.characters_present)
                missing = prev_characters - current_chars
                appearing = current_chars - prev_characters

                notes = []
                if missing:
                    notes.append(f"离开: {', '.join(missing)}")
                if appearing:
                    notes.append(f"加入: {', '.join(appearing)}")

                if notes and not scene.continuity_notes:
                    scene.continuity_notes = "; ".join(notes)

            prev_characters = set(scene.characters_present)


def estimate_scene_count(text_length: int) -> int:
    """根据文本长度预估场景数量。

    经验值：每 2000-3000 字约一个场景。

    Args:
        text_length: 章节文本长度（字符数）。

    Returns:
        预估的场景数量。
    """
    if text_length < 1000:
        return 1
    elif text_length < 3000:
        return 2
    elif text_length < 6000:
        return 3
    elif text_length < 10000:
        return 4
    elif text_length < 20000:
        return 6
    else:
        return 8
