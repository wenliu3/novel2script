"""novel2script — 数据模型。

宽松 Schema：所有字段都有默认值，兼容各种 LLM 输出格式。
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field, ConfigDict


# ═══════════════════════════════════════════════════════════════
# 角色（pipeline 内部使用，跨块合并）
# ═══════════════════════════════════════════════════════════════


class CharacterRole(str, Enum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MINOR = "minor"
    MENTIONED = "mentioned"


class CharacterRelation(BaseModel):
    target: str = Field(..., description="目标角色名")
    relation: str = Field("", description="关系类型")
    description: str = Field("", description="关系描述")
    strength: int = Field(5, ge=1, le=10)
    direction: str = Field("双向")


class Character(BaseModel):
    name: str = Field(..., description="角色中文名")
    english_name: str = Field("")
    aliases: list[str] = Field(default_factory=list)
    gender: str = Field("")
    age: str = Field("")
    role: CharacterRole = Field(CharacterRole.MINOR)
    importance: int = Field(0, ge=0, le=10)
    first_appearance: int = Field(0)
    appearance: str = Field("")
    personality: str = Field("")
    background: str = Field("")
    voice_tone: str = Field("")
    relations: list[CharacterRelation] = Field(default_factory=list)


class CharacterList(BaseModel):
    characters: list[Character] = Field(default_factory=list)

    def find_by_name(self, name: str) -> Character | None:
        for c in self.characters:
            if c.name == name or name in c.aliases or name == c.english_name:
                return c
        return None

    def merge(self, other: CharacterList) -> CharacterList:
        merged: dict[str, Character] = {}
        for c in self.characters:
            merged[c.name] = c.model_copy(deep=True)
        for other_c in other.characters:
            existing = merged.get(other_c.name)
            if existing:
                merged[other_c.name] = _merge_two_characters(existing, other_c)
            else:
                merged[other_c.name] = other_c.model_copy(deep=True)
        result = CharacterList(characters=list(merged.values()))
        result.characters.sort(key=lambda c: c.importance, reverse=True)
        return result



def _merge_two_characters(a: Character, b: Character) -> Character:
    aliases = list(set(a.aliases + b.aliases))
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
        ) if (a.first_appearance > 0 or b.first_appearance > 0) else 0,
        appearance=a.appearance or b.appearance,
        personality=a.personality or b.personality,
        background=a.background or b.background,
        voice_tone=a.voice_tone or b.voice_tone,
        relations=relations,
    )


# ═══════════════════════════════════════════════════════════════
# 剧本输出 Schema — 宽松版，所有字段有默认值
# ═══════════════════════════════════════════════════════════════


class DialogueLine(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["dialogue"] = "dialogue"
    character: str = Field("", description="角色名")
    text: str = Field("", description="对白内容")
    parenthetical: str | None = Field(None)


class Action(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["action"] = "action"
    text: str = Field("", description="动作描述")


ContentItem = Union[DialogueLine, Action, dict]


class Scene(BaseModel):
    """场景 — 所有字段可选，兼容 LLM 各种输出格式。"""
    model_config = ConfigDict(extra="allow")
    scene_number: int = Field(1, ge=1)
    heading: str = Field("")
    title: str = Field("")  # LLM 有时用 title 代替 heading
    location: str = Field("")
    time_of_day: str = Field("")
    int_ext: str = Field("")  # 不用 Literal，接受任何值
    characters: list[str] = Field(default_factory=list)
    content: list[ContentItem] = Field(default_factory=list)
    summary: str | None = Field(None)
    setting: str = Field("")  # LLM 有时用 setting
    description: str = Field("")  # LLM 有时用 description

    def get_heading(self) -> str:
        """获取场景标题，兼容多种字段名。"""
        return self.heading or self.title or self.setting or self.description or ""

    def get_location(self) -> str:
        """获取地点，兼容多种字段名。"""
        return self.location or ""


class Chapter(BaseModel):
    """章节 — 所有字段有默认值。"""
    model_config = ConfigDict(extra="allow")
    chapter_number: int = Field(1, ge=1)
    title: str = Field("")
    chapter_title: str = Field("")  # LLM 有时用 chapter_title
    scenes: list[Scene] = Field(default_factory=list)

    def get_title(self) -> str:
        return self.title or self.chapter_title or ""


class Screenplay(BaseModel):
    """完整剧本 — 所有字段有默认值，容忍缺失。"""
    model_config = ConfigDict(extra="allow")
    title: str = Field("未命名剧本")
    author: str | None = Field(None)
    genre: str | None = Field(None)
    characters: dict[str, str] = Field(default_factory=dict)
    chapters: list[Chapter] = Field(default_factory=list)

    @property
    def total_scenes(self) -> int:
        return sum(len(ch.scenes) for ch in self.chapters)

    @property
    def total_characters(self) -> int:
        return len(self.characters)


def fix_llm_data(data: dict) -> dict:
    """修复 LLM 输出的常见格式问题。"""
    if not isinstance(data, dict):
        return {"title": "未命名剧本", "chapters": []}

    # 确保有 title
    if "title" not in data:
        data["title"] = data.get("name", data.get("novel_title", "未命名剧本"))

    # 确保有 chapters
    if "chapters" not in data:
        # LLM 有时直接输出 scenes 列表
        if "scenes" in data:
            data["chapters"] = [{"chapter_number": 1, "title": "", "scenes": data.pop("scenes")}]
        else:
            data["chapters"] = []

    # 修复每个 chapter
    for ch in data["chapters"]:
        if not isinstance(ch, dict):
            continue

        # 确保有 scenes
        if "scenes" not in ch:
            ch["scenes"] = []

        # 修复每个 scene
        for scene in ch["scenes"]:
            if not isinstance(scene, dict):
                continue

            # heading 兼容：title → heading
            if not scene.get("heading") and scene.get("title"):
                scene["heading"] = scene["title"]

            # content 兼容：如果没有 content，尝试从其他字段构建
            if not scene.get("content"):
                # LLM 有时把内容放在 description、text、body 等字段
                desc = scene.get("description", "") or scene.get("text", "") or scene.get("body", "")
                if desc:
                    scene["content"] = [{"type": "action", "text": desc}]

            # 确保 content 中的每个 item 都是 dict
            if scene.get("content"):
                fixed_content = []
                for item in scene["content"]:
                    if isinstance(item, str):
                        fixed_content.append({"type": "action", "text": item})
                    elif isinstance(item, dict):
                        fixed_content.append(item)
                scene["content"] = fixed_content

    return data
