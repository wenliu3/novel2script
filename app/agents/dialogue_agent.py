"""对白生成 Agent（PR-05 核心模块）。

负责将小说场景叙述转换为结构化剧本节拍：
1. 提取动作描述 → action beats
2. 叙述转对白 → dialogue beats
3. 环境/氛围描写 → narration beats
4. 可选生成电影级镜头（shots）

输出 enrich 后的 Scene 对象（含 beats + shots）。
"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.schema.scene import Beat, DialogueLine, Scene, Shot
from app.services.llm_service import LLMService

MAX_SCENE_LENGTH = 8000


class DialogueAgent(BaseAgent):
    """对白生成 Agent。

    职责：
    1. 从场景叙述中提取节拍（动作 + 对白 + 旁白）
    2. 将小说间接叙述转换为具体对白
    3. 生成电影级镜头（可选，含机位、景别、画面描述）
    4. 标注说话者和情感状态
    """

    def __init__(self, llm: LLMService) -> None:
        super().__init__("dialogue_agent", llm)

    def execute(
        self,
        scene: Scene,
        chapter_text: str,
        chapter_number: int,
        character_names: list[str] | None = None,
    ) -> Scene:
        """为单个场景生成节拍和镜头。

        Args:
            scene: 场景基础信息（由 scene_agent 生成）。
            chapter_text: 章节原文（用于定位对话上下文）。
            chapter_number: 章节编号。
            character_names: 已知角色名列表。

        Returns:
            补充了 beats 和 shots 的完整 Scene 对象。
        """
        names_context = ""
        if character_names:
            names_context = (
                f"已知角色: {', '.join(character_names)}\n"
                f"请基于原文为这些角色生成合理的对白。"
            )

        prompt_user_parts = [
            f"场景标题: {scene.title}",
            f"地点: {scene.location}",
            f"时间: {scene.time}",
            f"氛围: {scene.mood}",
        ]
        if scene.props:
            prompt_user_parts.append(f"道具: {', '.join(scene.props)}")
        prompt_user_parts.append(f"\n原文片段:\n{chapter_text[:MAX_SCENE_LENGTH]}")
        prompt_user = "\n".join(prompt_user_parts)

        try:
            result = self.llm_prompt_json(
                "dialogue_translation",
                prompt_user,
                character_names=names_context,
            )
        except Exception as e:
            self.logger.error(f"  {scene.id} LLM 调用失败: {e}")
            return scene

        # 解析节拍
        beats = self._parse_beats(result.get("beats", []))
        scene.beats = beats

        # 解析镜头
        shots = self._parse_shots(result.get("shots", []), scene.id)
        scene.shots = shots

        action_count = len(scene.action_beats)
        dialogue_count = len(scene.dialogue_beats)
        self.logger.info(
            f"  {scene.id}: {len(beats)} beats "
            f"(action:{action_count} dialogue:{dialogue_count}), "
            f"{len(shots)} shots"
        )

        return scene

    def generate_beats(
        self,
        scene: Scene,
        chapter_text: str,
        character_names: list[str] | None = None,
    ) -> list[Beat]:
        """仅生成节拍（不生成镜头），更轻量的调用。

        Args:
            scene: 场景基础信息。
            chapter_text: 章节原文。
            character_names: 角色名列表。

        Returns:
            节拍列表。
        """
        scene = self.execute(scene, chapter_text, 0, character_names)
        return scene.beats

    # ── 内部方法 ──

    def _parse_beats(self, beats_data: list[dict[str, Any]]) -> list[Beat]:
        """从 LLM JSON 响应解析 Beat 对象列表。"""
        beats = []
        for b in beats_data:
            beat_type = b.get("type", "action")
            if beat_type not in ("action", "dialogue", "narration"):
                beat_type = "action"

            beats.append(
                Beat(
                    type=beat_type,
                    character=b.get("character", ""),
                    content=b.get("content", ""),
                )
            )
        return beats

    def _parse_shots(
        self, shots_data: list[dict[str, Any]], scene_id: str
    ) -> list[Shot]:
        """从 LLM JSON 响应解析 Shot 对象列表。"""
        shots = []
        for j, shot_data in enumerate(shots_data, 1):
            dialogue_lines = [
                DialogueLine(
                    character=d.get("character", ""),
                    line=d.get("line", ""),
                    emotion=d.get("emotion", ""),
                )
                for d in shot_data.get("dialogue", [])
            ]

            shot = Shot(
                id=f"{scene_id}_sh{j}",
                camera_angle=shot_data.get("camera_angle", ""),
                shot_type=shot_data.get("shot_type", ""),
                frame_description=shot_data.get("frame_description", ""),
                movement=shot_data.get("movement", "static"),
                duration_seconds=shot_data.get("duration_seconds", 5.0),
                dialogue=dialogue_lines,
                narration=shot_data.get("narration", ""),
                visual_effects=shot_data.get("visual_effects", ""),
            )
            shots.append(shot)
        return shots
