"""角色提取 Agent。

负责从章节内容中识别人物、提取角色信息、构建角色关系图谱。
使用 LLM 进行智能角色识别和关系分析。
"""

from app.agents.base_agent import BaseAgent
from app.schema.character import Character, CharacterList, CharacterRelation
from app.services.llm_service import LLMService


class CharacterAgent(BaseAgent):
    """角色提取 Agent。

    职责：
    1. 从章节文本中识别人物
    2. 提取角色属性（姓名、性别、性格等）
    3. 分析角色间关系
    4. 输出结构化的 CharacterList
    """

    def __init__(self, llm: LLMService) -> None:
        super().__init__("character_agent", llm)

    def execute(
        self,
        chapters_text: str,
        existing_characters: CharacterList | None = None,
    ) -> CharacterList:
        """从文本中提取角色信息。

        Args:
            chapters_text: 待分析的章节文本（可多章合并）。
            existing_characters: 已有的角色列表（增量更新时传入）。

        Returns:
            提取的角色列表。
        """
        existing_context = ""
        if existing_characters and existing_characters.characters:
            names = [c.name for c in existing_characters.characters]
            existing_context = f"\n已知角色: {', '.join(names)}\n请补充新发现的角色，并更新已有角色的信息。"

        # 文本过长时截断（避免超出上下文窗口）
        truncated = chapters_text[:15000] if len(chapters_text) > 15000 else chapters_text

        result = self.llm_prompt_json(
            "character_extraction",
            truncated + existing_context,
        )

        # 解析为 CharacterList
        characters = []
        for char_data in result.get("characters", []):
            relations = [
                CharacterRelation(**r) for r in char_data.get("relations", [])
            ]
            character = Character(
                name=char_data.get("name", ""),
                english_name=char_data.get("english_name", ""),
                aliases=char_data.get("aliases", []),
                gender=char_data.get("gender", ""),
                age=char_data.get("age", ""),
                appearance=char_data.get("appearance", ""),
                personality=char_data.get("personality", ""),
                background=char_data.get("background", ""),
                relations=relations,
            )
            characters.append(character)

        character_list = CharacterList(characters=characters)
        self.logger.info(f"提取到 {len(characters)} 个角色")
        return character_list
