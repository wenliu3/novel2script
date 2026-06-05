"""YAML 构建 Agent。

将所有 Agent 的输出组装为完整的 LRM 脚本 YAML 结构。
"""

from datetime import datetime, timezone

from app.agents.base_agent import BaseAgent
from app.schema.character import CharacterList
from app.schema.scene import Scene
from app.schema.script import ChapterScript, Script, ScriptMetadata
from app.services.llm_service import LLMService


class YAMLBuilderAgent(BaseAgent):
    """YAML 构建 Agent。

    职责：
    1. 聚合所有 Agent 的输出
    2. 组装为完整的 Script 数据结构
    3. 为每个元素生成唯一 ID
    4. 确保数据完整性
    """

    def __init__(self, llm: LLMService) -> None:
        super().__init__("yaml_builder", llm)

    def execute(
        self,
        novel_name: str,
        chapter_scripts: list[tuple[int, str, list[Scene]]],
    ) -> Script:
        """组装完整的脚本结构。

        Args:
            novel_name: 小说名称。
            chapter_scripts: 每章的 (章节编号, 章节标题, 场景列表) 元组。

        Returns:
            完整的 Script 对象。
        """
        chapters = []
        for number, title, scenes in chapter_scripts:
            chapter = ChapterScript(
                number=number,
                title=title,
                scenes=scenes,
            )
            chapters.append(chapter)

        total_scenes = sum(len(ch.scenes) for ch in chapters)

        script = Script(
            title=f"{novel_name} - LRM Script",
            metadata=ScriptMetadata(
                source_novel=novel_name,
                total_chapters=len(chapters),
                total_scenes=total_scenes,
                generated_at=datetime.now(timezone.utc).isoformat(),
            ),
            chapters=chapters,
        )

        self.logger.info(
            f"脚本组装完成: {len(chapters)} 章, {total_scenes} 个场景"
        )
        return script
