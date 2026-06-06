"""校验 Agent（PR-08 核心模块）。

验证生成的脚本是否完整、一致、符合格式要求，支持自动修复简单问题。

职责：
1. 结构完整性校验（title, metadata, chapters, scenes, beats, shots）
2. ID 唯一性校验（scene/shot/character）
3. Beat 内容校验（类型、内容非空、dialogue 必须含角色）
4. 角色引用校验（speaker_id 存在于 characters 列表）
5. 自动修复（空 ID、缺失字段、空 beat 角色等）
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base_agent import BaseAgent
from app.schema.script import Script
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

VALID_BEAT_TYPES = {"action", "dialogue", "narration"}


class ValidationResult:
    """校验结果。"""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.fixes_applied: list[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_fix(self, msg: str) -> None:
        self.fixes_applied.append(msg)

    def summary(self) -> str:
        parts = []
        if self.errors:
            parts.append(f"错误: {len(self.errors)}")
        if self.warnings:
            parts.append(f"警告: {len(self.warnings)}")
        if self.fixes_applied:
            parts.append(f"已修复: {len(self.fixes_applied)}")
        if not parts:
            return "校验通过 ✓"
        return ", ".join(parts)


class ValidatorAgent(BaseAgent):
    """校验 Agent。

    职责：
    1. 脚本结构完整性
    2. ID 唯一性
    3. Beat 内容校验
    4. 角色引用校验
    5. 自动修复简单问题
    """

    def __init__(self, llm: LLMService) -> None:
        super().__init__("validator_agent", llm)

    def execute(self, script: Script) -> ValidationResult:
        """校验脚本数据。

        Args:
            script: 待校验的脚本对象。

        Returns:
            校验结果。
        """
        result = ValidationResult()

        # ── 1. 基础结构校验 ──
        self._validate_structure(script, result)

        # ── 2. 角色校验 ──
        self._validate_characters(script, result)

        # ── 3. 章节与场景校验 ──
        seen_ids: set[str] = set()
        char_ids = {c.id for c in script.characters}

        for chapter in script.chapters:
            for scene in chapter.scenes:
                # ID 唯一性
                if scene.id in seen_ids:
                    result.add_error(f"重复的场景 ID: {scene.id}")
                seen_ids.add(scene.id)

                # 场景完整性
                if not scene.title:
                    result.add_warning(f"场景 {scene.id} 缺少标题")
                if not scene.location:
                    result.add_warning(f"场景 {scene.id} 缺少地点")

                # Beat 校验
                self._validate_beats(scene.id, scene.beats, char_ids, result)

                # Shot 校验
                self._validate_shots(scene.id, scene.shots, seen_ids, result)

        # ── 4. 自动修复 ──
        self._auto_fix(script, result)

        # ── 5. LLM 辅助内容校验 ──
        if script.chapters:
            self._llm_content_check(script, result)

        self.logger.info(f"校验完成: {result.summary()}")
        return result

    # ── 内部校验方法 ──

    def _validate_structure(self, script: Script, result: ValidationResult) -> None:
        """校验顶层结构。"""
        if not script.title:
            result.add_error("脚本缺少标题 (title)")

        if not script.metadata.source_novel:
            result.add_warning("缺少来源小说名")

        if not script.chapters:
            result.add_error("脚本没有章节 (chapters)")
            return

        if not script.genre:
            result.add_warning("未指定剧本类型 (genre)")

    def _validate_characters(self, script: Script, result: ValidationResult) -> None:
        """校验角色列表。"""
        if not script.characters:
            result.add_warning("脚本没有角色列表 (characters)")
            return

        seen_char_ids: set[str] = set()
        for char in script.characters:
            if not char.id:
                result.add_error("角色缺少 ID")
            elif char.id in seen_char_ids:
                result.add_error(f"重复的角色 ID: {char.id}")
            seen_char_ids.add(char.id)

            if not char.name:
                result.add_warning(f"角色 {char.id} 缺少姓名")

    def _validate_beats(
        self,
        scene_id: str,
        beats: list,
        char_ids: set[str],
        result: ValidationResult,
    ) -> None:
        """校验节拍列表。"""
        for i, beat in enumerate(beats):
            prefix = f"节拍 {scene_id}[{i}]"

            # 类型校验
            if beat.type not in VALID_BEAT_TYPES:
                result.add_error(f"{prefix}: 无效节拍类型 '{beat.type}'")

            # 内容非空
            if not beat.content:
                result.add_warning(f"{prefix}: 缺少内容")

            # dialogue 必须有角色
            if beat.type == "dialogue" and not beat.character:
                result.add_warning(f"{prefix}: 对白节拍缺少角色 (character)")

            # 角色引用存在性
            if beat.character and char_ids:
                # beat.character 可能是角色 ID 或角色名
                if beat.character.startswith("char_"):
                    if beat.character not in char_ids:
                        result.add_warning(
                            f"{prefix}: 引用了不存在的角色 ID '{beat.character}'"
                        )

    def _validate_shots(
        self,
        scene_id: str,
        shots: list,
        seen_ids: set[str],
        result: ValidationResult,
    ) -> None:
        """校验镜头列表。"""
        for shot in shots:
            if shot.id in seen_ids:
                result.add_error(f"重复的镜头 ID: {shot.id}")
            seen_ids.add(shot.id)

            if not shot.frame_description:
                result.add_warning(f"镜头 {shot.id} 缺少画面描述")

    # ── 自动修复 ──

    def _auto_fix(self, script: Script, result: ValidationResult) -> None:
        """自动修复简单问题。

        可修复：
        - 空 scene.id → 生成 ch{N}_s{M} 格式 ID
        - 空 shot.id → 生成 {scene_id}_sh{M} 格式 ID
        - 空 beat.type → 默认 "action"
        - dialogue beat 缺 character → 标记为 "未知"
        """
        for chapter in script.chapters:
            for scene in chapter.scenes:
                # 修复空 scene ID
                if not scene.id:
                    scene.id = (
                        f"ch{chapter.number}_s{len(chapter.scenes)}"
                    )
                    result.add_fix(f"自动生成场景 ID: {scene.id}")

                for j, shot in enumerate(scene.shots, 1):
                    # 修复空 shot ID
                    if not shot.id:
                        shot.id = f"{scene.id}_sh{j}"
                        result.add_fix(f"自动生成镜头 ID: {shot.id}")

                for i, beat in enumerate(scene.beats):
                    # 修复空 beat type
                    if not beat.type:
                        beat.type = "action"
                        result.add_fix(
                            f"{scene.id} beat[{i}] type → action"
                        )

                    # 修复 dialogue beat 缺角色
                    if beat.type == "dialogue" and not beat.character:
                        beat.character = "未知"
                        result.add_fix(
                            f"{scene.id} beat[{i}] character → 未知"
                        )

        # 修复空角色 ID
        for i, char in enumerate(script.characters):
            if not char.id:
                char.id = f"char_{i + 1:03d}"
                result.add_fix(f"自动生成角色 ID: {char.id}")

        # 修复空 genre
        if not script.genre:
            script.genre = "未分类"
            result.add_fix("genre → 未分类")

    def _llm_content_check(
        self, script: Script, result: ValidationResult
    ) -> None:
        """使用 LLM 进行内容一致性快速检查。"""
        if not script.chapters:
            return

        sample = script.chapters[:2]
        sample_text = str(
            {
                "title": script.title,
                "genre": script.genre,
                "chapters": [
                    {
                        "number": ch.number,
                        "scenes_count": len(ch.scenes),
                        "beats_count": sum(len(s.beats) for s in ch.scenes),
                    }
                    for ch in sample
                ],
            }
        )

        try:
            check_result = self.llm_prompt_json(
                "script_assembly",
                f"Quick consistency check for this script structure:\n{sample_text}",
            )
            if check_result.get("issues"):
                for issue in check_result["issues"]:
                    result.add_warning(f"LLM: {issue}")
        except Exception:
            self.logger.debug("LLM 内容校验跳过")
