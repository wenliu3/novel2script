"""场景拆分 Agent。

负责将章节文本拆分为独立场景，为每个场景生成描述信息。
"""

from app.agents.base_agent import BaseAgent
from app.schema.scene import Scene
from app.services.llm_service import LLMService


class SceneAgent(BaseAgent):
    """场景拆分 Agent。

    职责：
    1. 识别章节中的场景边界
    2. 为每个场景生成描述（地点、时间、氛围）
    3. 输出结构化的 Scene 列表
    """

    def __init__(self, llm: LLMService) -> None:
        super().__init__("scene_agent", llm)

    def execute(
        self,
        chapter_text: str,
        chapter_number: int,
        character_names: list[str] | None = None,
    ) -> list[Scene]:
        """将章节拆分为场景。

        Args:
            chapter_text: 章节原文。
            chapter_number: 章节编号（用于生成场景 ID）。
            character_names: 已知角色名列表（可选，用于上下文）。

        Returns:
            拆分后的场景列表。
        """
        names_context = ""
        if character_names:
            names_context = f"\n已知角色: {', '.join(character_names)}"

        truncated = chapter_text[:12000] if len(chapter_text) > 12000 else chapter_text

        result = self.llm_prompt_json(
            "scene_splitting",
            truncated,
            chapter_number=str(chapter_number),
            character_names=names_context,
        )

        scenes = []
        for i, scene_data in enumerate(result.get("scenes", []), 1):
            scene = Scene(
                id=f"ch{chapter_number}_s{i}",
                title=scene_data.get("title", f"Scene {i}"),
                location=scene_data.get("location", ""),
                time=scene_data.get("time", ""),
                mood=scene_data.get("mood", ""),
                props=scene_data.get("props", []),
            )
            scenes.append(scene)

        self.logger.info(f"第{chapter_number}章拆分为 {len(scenes)} 个场景")
        return scenes
