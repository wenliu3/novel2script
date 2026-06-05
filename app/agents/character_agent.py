"""角色分析 Agent（PR-04）。

负责从章节内容中识别人物、提取角色信息、构建角色关系图谱。
支持逐章增量处理，跨章角色合并，重要性评分和关系图谱构建。

职责：
1. 逐章识别角色，提取角色属性（姓名、别名、性别、性格等）
2. 跨章合并角色信息，去重并补充完善
3. 分析角色间关系（关系类型、强度、方向、随时间变化）
4. 构建完整的关系图谱（nodes + edges）
5. 评估角色重要性
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from app.agents.base_agent import BaseAgent
from app.schema.character import (
    Character,
    CharacterAnalysisResult,
    CharacterGraph,
    CharacterList,
    CharacterRelation,
    ChapterCharacterAppearance,
)
from app.schema.chapter import Chapter
from app.services.llm_service import LLMService


class CharacterAgent(BaseAgent):
    """角色分析 Agent。

    将章节文本逐章送入 LLM 提取角色，
    跨章合并角色信息，最后构建关系图谱。
    """

    def __init__(self, llm: LLMService) -> None:
        super().__init__("character_agent", llm)

    def execute(
        self,
        chapters_text: str,
        chapters: list[Chapter] | None = None,
        existing_characters: CharacterList | None = None,
    ) -> CharacterAnalysisResult:
        """从文本中提取完整的角色分析结果。

        Args:
            chapters_text: 待分析的章节文本（所有章节合并，用于单次分析）。
            chapters: 章节对象列表（用于逐章增量分析，推荐）。
            existing_characters: 已有的角色列表（增量更新时传入）。

        Returns:
            完整的角色分析结果，包含角色列表、关系图谱和各章出场信息。
        """
        if chapters:
            return self._analyze_by_chapters(chapters, existing_characters)

        return self._analyze_bulk(chapters_text, existing_characters)

    def _analyze_by_chapters(
        self,
        chapters: list[Chapter],
        existing_characters: CharacterList | None = None,
    ) -> CharacterAnalysisResult:
        """逐章分析角色。

        每一章单独调用 LLM 提取角色信息，再跨章合并，
        最后构建全局关系图谱。

        Args:
            chapters: 章节对象列表。
            existing_characters: 已有角色列表。

        Returns:
            完整的角色分析结果。
        """
        aggregated = (
            copy.deepcopy(existing_characters)
            if existing_characters
            else CharacterList()
        )
        chapter_appearances: list[ChapterCharacterAppearance] = []
        known_names: set[str] = set(
            c.name for c in aggregated.characters
        )

        for ch in chapters:
            self.logger.info(f"分析第{ch.number}章角色: {ch.title}")

            existing_context = ""
            if aggregated.characters:
                names = [c.name for c in aggregated.characters]
                existing_context = (
                    f"\n已有角色列表: {', '.join(names)}\n"
                    f"请基于本章内容更新已有角色的信息，并补充新发现的角色。"
                )

            text = ch.raw_text or ""
            truncated = text[:12000] if len(text) > 12000 else text

            result = self.llm_prompt_json(
                "character_extraction",
                truncated + existing_context,
            )

            # 解析本章出场信息
            chap_info = self._parse_chapter_appearance(result, ch)
            chapter_appearances.append(chap_info)

            # 合并角色
            new_this_chapter: list[str] = []
            for char_data in result.get("characters", []):
                char_name = char_data.get("name", "")
                if not char_name:
                    continue

                if char_name in known_names:
                    existing = aggregated.find_by_name(char_name)
                    if existing:
                        self._merge_character(existing, char_data, ch.number)
                else:
                    character = self._build_character(
                        char_data, ch.number
                    )
                    aggregated.characters.append(character)
                    known_names.add(char_name)
                    new_this_chapter.append(char_name)

            chap_info.new_characters = new_this_chapter
            self.logger.info(
                f"  本角色: {len(result.get('characters', []))} 个, "
                f"新角色: {len(new_this_chapter)} 个"
            )

        # 构建关系图谱
        relation_graph = aggregated.get_relation_graph()

        self.logger.info(
            f"角色分析完成: 共 {len(aggregated.characters)} 个角色, "
            f"{len(relation_graph.edges)} 条关系"
        )

        return CharacterAnalysisResult(
            character_list=aggregated,
            relation_graph=relation_graph,
            chapter_appearances=chapter_appearances,
            total_chapters=len(chapters),
        )

    def _analyze_bulk(
        self,
        chapters_text: str,
        existing_characters: CharacterList | None = None,
    ) -> CharacterAnalysisResult:
        """批量分析角色（所有章节文本合并一次调用）。

        适用于章节较少或文本较短的场景。

        Args:
            chapters_text: 合并后的所有章节文本。
            existing_characters: 已有角色列表。

        Returns:
            完整的角色分析结果。
        """
        existing_context = ""
        if existing_characters and existing_characters.characters:
            names = [c.name for c in existing_characters.characters]
            existing_context = (
                f"\n已有角色列表: {', '.join(names)}\n"
                f"请补充新发现的角色，并更新已有角色的信息。"
            )

        truncated = (
            chapters_text[:15000]
            if len(chapters_text) > 15000
            else chapters_text
        )

        result = self.llm_prompt_json(
            "character_extraction",
            truncated + existing_context,
        )

        characters = []
        for char_data in result.get("characters", []):
            character = self._build_character(char_data, 1)
            characters.append(character)

        character_list = CharacterList(characters=characters)
        relation_graph = character_list.get_relation_graph()

        # 尝试解析章节信息
        chap_info = None
        chap_raw = result.get("chapter_characters")
        if chap_raw:
            chap_info = ChapterCharacterAppearance(
                chapter_number=chap_raw.get("chapter_number", 1),
                chapter_title=chap_raw.get("chapter_title", ""),
                characters=chap_raw.get("characters", []),
                main_character=chap_raw.get("main_character", ""),
                new_characters=chap_raw.get("new_characters", []),
                key_relations=chap_raw.get("key_relations", []),
            )

        chapter_appearances = [chap_info] if chap_info else []

        self.logger.info(
            f"批量角色分析: {len(characters)} 个角色, "
            f"{len(relation_graph.edges)} 条关系"
        )

        return CharacterAnalysisResult(
            character_list=character_list,
            relation_graph=relation_graph,
            chapter_appearances=chapter_appearances,
            total_chapters=1,
        )

    def _parse_chapter_appearance(
        self,
        result: dict[str, Any],
        chapter: Chapter,
    ) -> ChapterCharacterAppearance:
        """从 LLM 输出中解析本章出场信息。"""
        chap_raw = result.get("chapter_characters", {})
        return ChapterCharacterAppearance(
            chapter_number=chapter.number,
            chapter_title=chapter.title or f"第{chapter.number}章",
            characters=chap_raw.get("characters", []),
            main_character=chap_raw.get("main_character", ""),
            new_characters=chap_raw.get("new_characters", []),
            key_relations=chap_raw.get("key_relations", []),
        )

    def _build_character(
        self,
        char_data: dict[str, Any],
        chapter_number: int,
    ) -> Character:
        """从 LLM 输出构建 Character 对象。"""
        relations = [
            CharacterRelation(
                target=r.get("target", ""),
                relation=r.get("relation", ""),
                description=r.get("description", ""),
                strength=r.get("strength", 5),
                direction=r.get("direction", "双向"),
                evidence_chapters=[chapter_number],
                change_over_time=r.get("change_over_time", ""),
            )
            for r in char_data.get("relations", [])
            if r.get("target")
        ]

        return Character(
            name=char_data.get("name", ""),
            english_name=char_data.get("english_name", ""),
            aliases=char_data.get("aliases", []),
            gender=char_data.get("gender", ""),
            age=char_data.get("age", ""),
            appearance=char_data.get("appearance", ""),
            personality=char_data.get("personality", ""),
            background=char_data.get("background", ""),
            role_type=char_data.get("role_type", "配角"),
            importance_score=float(char_data.get("importance_score", 0.0)),
            first_appearance=chapter_number,
            last_appearance=chapter_number,
            appearance_chapters=[chapter_number],
            total_dialogue_lines=0,
            relations=relations,
        )

    def _merge_character(
        self,
        existing: Character,
        char_data: dict[str, Any],
        chapter_number: int,
    ) -> None:
        """将新章节提取的角色信息合并到已有角色中。"""
        # 合并别名
        new_aliases = char_data.get("aliases", [])
        existing_aliases_set = set(existing.aliases)
        for alias in new_aliases:
            if alias and alias not in existing_aliases_set:
                existing.aliases.append(alias)
                existing_aliases_set.add(alias)

        # 更新出场章节
        if chapter_number not in existing.appearance_chapters:
            existing.appearance_chapters.append(chapter_number)
        existing.last_appearance = max(
            existing.last_appearance, chapter_number
        )

        # 更新属性（新数据覆盖旧数据，但保留非空值）
        if char_data.get("english_name") and not existing.english_name:
            existing.english_name = char_data["english_name"]
        if char_data.get("gender") and not existing.gender:
            existing.gender = char_data["gender"]
        if char_data.get("age") and not existing.age:
            existing.age = char_data["age"]
        if char_data.get("appearance") and not existing.appearance:
            existing.appearance = char_data["appearance"]
        if char_data.get("personality") and not existing.personality:
            existing.personality = char_data["personality"]
        if char_data.get("background") and not existing.background:
            existing.background = char_data["background"]

        # 更新角色定位（保留更重要的）
        role_type_priority = {"主角": 4, "重要配角": 3, "配角": 2, "龙套": 1}
        new_role = char_data.get("role_type", "配角")
        if role_type_priority.get(new_role, 0) > role_type_priority.get(
            existing.role_type, 0
        ):
            existing.role_type = new_role

        # 更新重要性评分（取最大值）
        new_score = float(char_data.get("importance_score", 0.0))
        if new_score > existing.importance_score:
            existing.importance_score = new_score

        # 合并关系
        existing_targets = {
            r.target: r for r in existing.relations
        }
        for r_data in char_data.get("relations", []):
            target = r_data.get("target", "")
            if not target:
                continue

            if target in existing_targets:
                existing_rel = existing_targets[target]
                # 更新关系强度（取平均值）
                new_strength = r_data.get("strength", 5)
                if chapter_number not in existing_rel.evidence_chapters:
                    existing_rel.evidence_chapters.append(chapter_number)
                    # 当有多个章节证据时，取平均强度
                    total = existing_rel.strength * (
                        len(existing_rel.evidence_chapters) - 1
                    ) + new_strength
                    existing_rel.strength = round(
                        total / len(existing_rel.evidence_chapters)
                    )
                # 更新关系变化描述
                if r_data.get("change_over_time"):
                    existing_rel.change_over_time = r_data[
                        "change_over_time"
                    ]
                if r_data.get("description"):
                    existing_rel.description = r_data["description"]
            else:
                new_rel = CharacterRelation(
                    target=target,
                    relation=r_data.get("relation", ""),
                    description=r_data.get("description", ""),
                    strength=r_data.get("strength", 5),
                    direction=r_data.get("direction", "双向"),
                    evidence_chapters=[chapter_number],
                    change_over_time=r_data.get("change_over_time", ""),
                )
                existing.relations.append(new_rel)

    def get_character_summary(
        self, result: CharacterAnalysisResult
    ) -> dict:
        """生成角色分析的摘要报告。

        Args:
            result: 角色分析结果。

        Returns:
            包含摘要信息的字典。
        """
        cl = result.character_list
        graph = result.relation_graph

        sorted_chars = cl.get_characters_sorted_by_importance()
        top_chars = [
            {
                "name": c.name,
                "role_type": c.role_type,
                "importance": c.importance_score,
                "appearances": len(c.appearance_chapters),
                "relations_count": len(c.relations),
            }
            for c in sorted_chars[:10]
        ]

        return {
            "total_characters": len(cl.characters),
            "total_relationships": len(graph.edges),
            "protagonists": len(cl.get_protagonists()),
            "total_chapters_analyzed": result.total_chapters,
            "top_characters": top_chars,
            "graph_summary": graph.get_summary(),
        }
