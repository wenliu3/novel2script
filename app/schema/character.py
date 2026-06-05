"""角色数据模型。

定义小说角色的信息结构，包括基本信息、性格特征、角色关系等。
"""

from pydantic import BaseModel, Field


class CharacterRelation(BaseModel):
    """角色关系。"""

    target: str = Field(..., description="关系目标角色名")
    relation: str = Field(..., description="关系类型，如：师徒、兄弟、敌人")
    description: str = Field("", description="关系描述")


class Character(BaseModel):
    """角色信息。"""

    name: str = Field(..., description="角色姓名（中文）")
    english_name: str = Field("", description="英文名/翻译名")
    aliases: list[str] = Field(default_factory=list, description="别名列表")
    gender: str = Field("", description="性别")
    age: str = Field("", description="年龄描述")
    appearance: str = Field("", description="外貌特征")
    personality: str = Field("", description="性格描述")
    background: str = Field("", description="背景故事")
    relations: list[CharacterRelation] = Field(
        default_factory=list, description="与其他角色的关系"
    )


class CharacterList(BaseModel):
    """角色列表（由 character_agent 输出）。"""

    characters: list[Character] = Field(default_factory=list)

    def find_by_name(self, name: str) -> Character | None:
        """按姓名查找角色。"""
        for c in self.characters:
            if c.name == name or name in c.aliases:
                return c
        return None
