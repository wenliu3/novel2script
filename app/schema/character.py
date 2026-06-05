"""角色数据模型。

定义小说角色的信息结构，包括基本信息、性格特征、角色关系、关系图谱等。
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
<<<<<<< HEAD
    relation: str = Field(..., description="关系类型，如：师徒、兄弟、敌人")
    description: str = Field("", description="关系描述（英文）")
=======
    relation: str = Field(..., description="关系类型，如：师徒、兄弟、敌人、恋人")
    description: str = Field("", description="关系描述")
    strength: int = Field(5, ge=1, le=10, description="关系强度（1-10）")
    direction: str = Field("双向", description="关系方向：双向、A→B、B→A")
    evidence_chapters: list[int] = Field(
        default_factory=list, description="支撑该关系的章节编号"
    )
    change_over_time: str = Field(
        "", description="关系随时间的变化（从敌对到友好等）"
    )
>>>>>>> main


class Character(BaseModel):
    """角色信息。"""

    name: str = Field(..., description="角色姓名（中文）")
    english_name: str = Field("", description="英文名/翻译名")
<<<<<<< HEAD
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
=======
    aliases: list[str] = Field(default_factory=list, description="别名/绰号列表")
    gender: str = Field("", description="性别")
    age: str = Field("", description="年龄/年龄描述")
    appearance: str = Field("", description="外貌特征")
    personality: str = Field("", description="性格描述")
    background: str = Field("", description="背景故事")
    role_type: str = Field("配角", description="角色定位：主角、重要配角、配角、龙套")
    importance_score: float = Field(0.0, ge=0.0, le=1.0, description="重要性评分（0-1）")
    first_appearance: int = Field(0, description="首次出场章节")
    last_appearance: int = Field(0, description="最后出场章节")
    appearance_chapters: list[int] = Field(
        default_factory=list, description="出场章节编号列表"
    )
    total_dialogue_lines: int = Field(0, description="总对话行数（估算）")
>>>>>>> main
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
<<<<<<< HEAD
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
=======
            if c.english_name == english_name:
                return c
        return None

    def get_protagonists(self) -> list[Character]:
        """获取主角列表。"""
        return [c for c in self.characters if c.role_type == "主角"]

    def get_characters_sorted_by_importance(self) -> list[Character]:
        """按重要性降序排列。"""
        return sorted(
            self.characters, key=lambda c: c.importance_score, reverse=True
        )

    def get_relation_graph(self) -> "CharacterGraph":
        """从角色关系中构建关系图谱。"""
        nodes = []
        edges = []

        for char in self.characters:
            nodes.append(
                CharacterNode(
                    id=char.name,
                    name=char.name,
                    english_name=char.english_name,
                    role_type=char.role_type,
                    importance_score=char.importance_score,
                    appearance_count=len(char.appearance_chapters),
                )
            )
            for rel in char.relations:
                # 避免重复边（A→B 和 B→A）
                edge_key = tuple(sorted([char.name, rel.target]))
                if not any(
                    e.source == rel.target and e.target == char.name for e in edges
                ):
                    edges.append(
                        CharacterEdge(
                            source=char.name,
                            target=rel.target,
                            relation=rel.relation,
                            description=rel.description,
                            strength=rel.strength,
                            direction=rel.direction,
                        )
                    )

        return CharacterGraph(nodes=nodes, edges=edges)


class CharacterNode(BaseModel):
    """关系图谱中的节点。"""

    id: str = Field(..., description="节点唯一标识")
    name: str = Field(..., description="角色名")
    english_name: str = Field("", description="英文名")
    role_type: str = Field("配角", description="角色定位")
    importance_score: float = Field(0.0, ge=0.0, le=1.0, description="重要性评分")
    appearance_count: int = Field(0, description="出场章节数")


class CharacterEdge(BaseModel):
    """关系图谱中的边。"""

    source: str = Field(..., description="源角色名")
    target: str = Field(..., description="目标角色名")
    relation: str = Field(..., description="关系类型")
    description: str = Field("", description="关系描述")
    strength: int = Field(5, ge=1, le=10, description="关系强度")
    direction: str = Field("双向", description="关系方向")


class CharacterGraph(BaseModel):
    """角色关系图谱（用于可视化/网络分析）。"""

    nodes: list[CharacterNode] = Field(default_factory=list)
    edges: list[CharacterEdge] = Field(default_factory=list)

    def get_summary(self) -> dict:
        """获取图谱摘要信息。"""
        return {
            "total_characters": len(self.nodes),
            "total_relationships": len(self.edges),
            "protagonists": len(
                [n for n in self.nodes if n.role_type == "主角"]
            ),
            "avg_importance": (
                sum(n.importance_score for n in self.nodes) / len(self.nodes)
                if self.nodes
                else 0
            ),
        }


class ChapterCharacterAppearance(BaseModel):
    """单章角色出场信息。"""

    chapter_number: int = Field(..., description="章节编号")
    chapter_title: str = Field("", description="章节标题")
    characters: list[str] = Field(
        default_factory=list, description="本出场角色名列表"
    )
    main_character: str = Field("", description="本章核心角色（视角角色）")
    new_characters: list[str] = Field(
        default_factory=list, description="本章首次出场的角色"
    )
    key_relations: list[dict] = Field(
        default_factory=list,
        description="本章关键关系变化，如 [{\"source\": \"A\", \"target\": \"B\", \"change\": \"从敌对到合作\"}]",
    )


class CharacterAnalysisResult(BaseModel):
    """角色分析的完整输出结果。"""

    character_list: CharacterList = Field(
        default_factory=CharacterList, description="完整的角色列表"
    )
    relation_graph: CharacterGraph = Field(
        default_factory=CharacterGraph, description="关系图谱"
    )
    chapter_appearances: list[ChapterCharacterAppearance] = Field(
        default_factory=list, description="各章出场信息"
    )
    total_chapters: int = Field(0, description="总分析章节数")
>>>>>>> main
