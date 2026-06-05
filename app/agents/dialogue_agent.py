"""对话处理 Agent。

负责提取场景中的对话、翻译为英文、标注情感。
"""

from app.agents.base_agent import BaseAgent
from app.schema.scene import DialogueLine, Scene, Shot
from app.services.llm_service import LLMService


class DialogueAgent(BaseAgent):
    """对话处理 Agent。

    职责：
    1. 从场景文本中提取对话
    2. 翻译为英文
    3. 标注说话者和情感
    4. 为每个场景生成镜头列表（含对话、旁白、画面描述）
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
        """为单个场景生成镜头和对话。

        Args:
            scene: 场景基础信息（由 scene_agent 生成）。
            chapter_text: 章节原文（用于定位对话上下文）。
            chapter_number: 章节编号。
            character_names: 已知角色名列表。

        Returns:
            补充了 shots 和 dialogue 的完整 Scene 对象。
        """
        names_context = ""
        if character_names:
            names_context = f"\n已知角色: {', '.join(character_names)}"

        prompt_user = (
            f"## Scene: {scene.title}\n"
            f"Location: {scene.location}\n"
            f"Time: {scene.time}\n"
            f"Mood: {scene.mood}\n\n"
            f"## Chapter Text (reference)\n{chapter_text[:10000]}\n"
            f"{names_context}"
        )

        result = self.llm_prompt_json(
            "dialogue_translation",
            prompt_user,
            scene_id=scene.id,
        )

        # 解析镜头数据
        shots = []
        for j, shot_data in enumerate(result.get("shots", []), 1):
            dialogue_lines = [
                DialogueLine(
                    character=d.get("character", ""),
                    line=d.get("line", ""),
                    emotion=d.get("emotion", ""),
                )
                for d in shot_data.get("dialogue", [])
            ]

            shot = Shot(
                id=f"{scene.id}_sh{j}",
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

        scene.shots = shots
        self.logger.info(f"  {scene.id}: 生成 {len(shots)} 个镜头")
        return scene
