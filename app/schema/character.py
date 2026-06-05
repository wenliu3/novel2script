"""角色数据模型。

定义小说角色的信息结构，包括基本信息、性格特征、角色关系等。
"""

from enum import Enum

from pydantic import BaseModel, Field


class CharacterRole(str, Enum):
    """角色在故事中的定位。"""

    PROTAGONIST = "protagonist"      # 主角
    ANTAGONIST = "antagonist"        # 反派
    SUPPORTING = "supporting"        # 重要配角
    MINOR = "minor"                  # 次要角色
    MENTIONED = "mentioned"          # 仅被提及


class CharacterRelation(BaseModel):
    """角色关系。"""

    target: str = Field(..., description="关系目标角色名")
    relation: str = Field(..., description="关系类型，如：师徒、兄弟、敌人")
    description: str = Field("", description="关系描述（英文）")


class Character(BaseModel):
    """角色信息。"""

    name: str = Field(..., description="角色姓名（中文）")
    english_name: str = Field("", description="英文名/翻译名")
    aliases: list[str] = Field(default_factory=list, description="别名列表")
    gender: str = Field("", description="性别: 男/女/未知")
    age: str = Field("", description="年龄描述")
    role: CharacterRole = Field(CharacterRole.MINOR, description="角色定位")
    importance: int = Field(0, description="重要度评分 0-10，基于出场频率和剧情影响")
    first_appearance: int = Field(0, description="首次出场章节编号")
    appearance: str = Field("", description="外貌特征（英文，供视频生成参考）")
    personality: str = Field("", description="性格描述（英文）")
    background: str = Field("", description="背景故事（英文）")
    voice_tone: str = Field("", description="说话风格/语气特征（英文）")
    relations: list[CharacterRelation] = Field(
        default_factory=list, description="与其他角色的关系"
    )


class CharacterList(BaseModel):
    """角色列表（由 character_agent 输出）。"""

    characters: list[Character] = Field(default_factory=list)

    def find_by_name(self, name: str) -> Character | None:
        """按姓名或别名查找角色。"""
        for c in self.characters:
            if c.name == name or name in c.aliases or name == c.english_name:
                return c
        return None

    def find_by_english_name(self, english_name: str) -> Character | None:
        """按英文名查找角色。"""
        for c in self.characters:
            if c.english_name.lower() == english_name.lower():
                return c
        return None

    def get_main_characters(self, min_importance: int = 5) -> list[Character]:
        """获取主要角色（重要度 >= min_importance）。"""
        return sorted(
            [c for c in self.characters if c.importance >= min_importance],
            key=lambda c: c.importance,
            reverse=True,
        )

    def merge(self, other: "CharacterList") -> "CharacterList":
        """合并另一个角色列表（增量分析时使用）。

        规则：
        - 同名角色合并信息（新信息覆盖旧信息）
        - 新角色直接添加
        - 关系列表去重合并
        - 重要度取最高值
        """
        merged: dict[str, Character] = {}

        # 先放入当前列表
        for c in self.characters:
            merged[c.name] = c.model_copy(deep=True)

        # 合并另一个列表
        for other_c in other.characters:
            existing = merged.get(other_c.name)
            if existing:
                merged[other_c.name] = _merge_characters(existing, other_c)
            else:
                merged[other_c.name] = other_c.model_copy(deep=True)

        result = CharacterList(characters=list(merged.values()))
        result.characters.sort(key=lambda c: c.importance, reverse=True)
        return result

    def to_markdown(self) -> str:
        """导出为 Markdown 格式的角色卡片。"""
        lines = ["# 角色图谱\n"]
        for c in self.characters:
            lines.append(f"## {c.name}")
            if c.english_name:
                lines.append(f"**English:** {c.english_name}")
            if c.aliases:
                lines.append(f"**别名:** {', '.join(c.aliases)}")
            lines.append(f"**定位:** {c.role.value} | **重要度:** {c.importance}/10")
            if c.gender:
                lines.append(f"**性别:** {c.gender}")
            if c.age:
                lines.append(f"**年龄:** {c.age}")
            if c.appearance:
                lines.append(f"**外貌:** {c.appearance}")
            if c.personality:
                lines.append(f"**性格:** {c.personality}")
            if c.voice_tone:
                lines.append(f"**语气:** {c.voice_tone}")
            if c.background:
                lines.append(f"**背景:** {c.background}")
            if c.relations:
                lines.append("\n**关系:**")
                for r in c.relations:
                    lines.append(f"  - {r.target}: {r.relation} — {r.description}")
            lines.append("")
        return "\n".join(lines)


def _merge_characters(a: Character, b: Character) -> Character:
    """合并两个同名角色的信息。策略：非空值优先，重要度取最高。"""
    # 别名合并
    aliases = list(set(a.aliases + b.aliases))

    # 关系合并（按 target 去重）
    relations = list(a.relations)
    seen_targets = {r.target for r in relations}
    for r in b.relations:
        if r.target not in seen_targets:
            relations.append(r)
            seen_targets.add(r.target)

    return Character(
        name=a.name,
        english_name=a.english_name or b.english_name,
        aliases=aliases,
        gender=a.gender or b.gender,
        age=a.age or b.age,
        role=a.role if a.importance >= b.importance else b.role,
        importance=max(a.importance, b.importance),
        first_appearance=min(
            a.first_appearance if a.first_appearance > 0 else 99999,
            b.first_appearance if b.first_appearance > 0 else 99999,
        ) or 0,
        appearance=a.appearance or b.appearance,
        personality=a.personality or b.personality,
        background=a.background or b.background,
        voice_tone=a.voice_tone or b.voice_tone,
        relations=relations,
    )
