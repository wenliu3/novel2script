<<<<<<< HEAD
"""人物分析 Agent。

从章节文本中智能提取、分析、合并角色信息，构建完整的角色图谱。
支持长文本分批处理、跨章节角色合并、重要度排序、关系图谱构建。
"""

import re
import logging
from pathlib import Path

from app.agents.base_agent import BaseAgent
from app.schema.character import Character, CharacterList, CharacterRelation, CharacterRole
=======
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
>>>>>>> main
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# 单次 LLM 调用的最大文本长度（留足上下文空间给提示词和输出）
CHUNK_SIZE = 8000

# 角色重要度阈值
IMPORTANCE_THRESHOLD = 3  # 低于此值的角色视为龙套，不进入最终图谱


class CharacterAgent(BaseAgent):
<<<<<<< HEAD
    """人物分析 Agent。

    完整流程：
    1. 分批读取章节文本（避免超出 LLM 上下文窗口）
    2. 每批提取角色信息
    3. 跨批次合并同名角色（别名匹配、信息补充）
    4. 按重要度排序、标注角色定位
    5. 构建角色关系图谱
    6. 输出 CharacterList

    Attributes:
        name: Agent 名称。
        llm: LLM 服务实例。
        chunk_size: 单次处理的最大文本长度。
        min_importance: 最低重要度阈值。
=======
    """角色分析 Agent。

    将章节文本逐章送入 LLM 提取角色，
    跨章合并角色信息，最后构建关系图谱。
>>>>>>> main
    """

    def __init__(
        self,
        llm: LLMService,
        chunk_size: int = CHUNK_SIZE,
        min_importance: int = IMPORTANCE_THRESHOLD,
    ) -> None:
        super().__init__("character_agent", llm)
        self.chunk_size = chunk_size
        self.min_importance = min_importance

    def execute(
        self,
        chapters_text: str,
        chapters: list[Chapter] | None = None,
        existing_characters: CharacterList | None = None,
<<<<<<< HEAD
        chapter_ranges: list[tuple[int, int]] | None = None,
    ) -> CharacterList:
        """执行人物分析。

        Args:
            chapters_text: 待分析的章节文本（可多章合并）。
            existing_characters: 已有的角色列表（增量分析时传入）。
            chapter_ranges: 每段文本对应的章节编号范围 [(start, end), ...]，
                           用于记录角色首次出场章节。为 None 时不影响分析。

        Returns:
            分析后的角色列表，按重要度降序排列。
=======
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
>>>>>>> main
        """
        self.logger.info(f"开始人物分析，文本长度: {len(chapters_text):,} 字符")

        # ── Step 1: 分批提取 ──
        chunks = self._split_into_chunks(chapters_text)
        self.logger.info(f"分为 {len(chunks)} 个文本块进行分析")

        all_characters = CharacterList()
        for i, chunk in enumerate(chunks):
            self.logger.info(f"  分析第 {i+1}/{len(chunks)} 块...")
            chunk_characters = self._extract_from_chunk(chunk, i + 1, len(chunks))
            all_characters = all_characters.merge(chunk_characters)

        self.logger.info(f"分批提取完成: {len(all_characters.characters)} 个角色（合并前）")

        # ── Step 2: 合并已有角色 ──
        if existing_characters and existing_characters.characters:
<<<<<<< HEAD
            all_characters = existing_characters.merge(all_characters)
            self.logger.info(f"与已有角色合并后: {len(all_characters.characters)} 个角色")

        # ── Step 3: 后处理 ──
        all_characters = self._post_process(all_characters)
=======
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
>>>>>>> main

        # ── Step 4: 过滤低重要度角色 ──
        filtered = CharacterList(
            characters=[
                c for c in all_characters.characters
                if c.importance >= self.min_importance
            ]
        )

<<<<<<< HEAD
        self.logger.info(
            f"人物分析完成: {len(filtered.characters)} 个角色 "
            f"(过滤前 {len(all_characters.characters)} 个, "
            f"阈值 >= {self.min_importance})"
        )

        return filtered

    # ──────────────────────────────────────────────
    # 内部方法
    # ──────────────────────────────────────────────

    def _split_into_chunks(self, text: str) -> list[str]:
        """将长文本按段落边界切分为多个块。

        优先在章节分隔符（=== 第X章 ===）处切分，
        其次在段落边界（空行）处切分，
        最后在句子边界处切分。

        Args:
            text: 原始文本。

        Returns:
            文本块列表，每块不超过 chunk_size 字符。
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        # 按章节分隔符切分
        sections = re.split(r"\n===\s*第?\d+章\s*===\n", text)

        current_chunk = ""
        for section in sections:
            if len(current_chunk) + len(section) <= self.chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + section
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # 如果单个 section 超过 chunk_size，按段落切分
                if len(section) > self.chunk_size:
                    sub_chunks = self._split_by_paragraphs(section)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = section

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text[:self.chunk_size]]

    def _split_by_paragraphs(self, text: str) -> list[str]:
        """按段落边界切分超长文本。"""
        paragraphs = text.split("\n\n")
        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) <= self.chunk_size:
                current += ("\n\n" if current else "") + para
            else:
                if current:
                    chunks.append(current)
                # 单段落超长，按句子切分
                if len(para) > self.chunk_size:
                    sent_chunks = self._split_by_sentences(para)
                    chunks.extend(sent_chunks)
                    current = ""
                else:
                    current = para
        if current:
            chunks.append(current)
        return chunks

    def _split_by_sentences(self, text: str) -> list[str]:
        """按句子边界切分（中文句号、问号、感叹号）。"""
        sentences = re.split(r"(?<=[。！？\.\!\?])\s*", text)
        chunks = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) <= self.chunk_size:
                current += sent
            else:
                if current:
                    chunks.append(current)
                current = sent
        if current:
            chunks.append(current)
        return chunks

    def _extract_from_chunk(
        self, chunk: str, chunk_index: int, total_chunks: int
    ) -> CharacterList:
        """从单个文本块中提取角色信息。

        Args:
            chunk: 文本块内容。
            chunk_index: 当前块编号（从 1 开始）。
            total_chunks: 总块数。

        Returns:
            本块提取的角色列表。
        """
        system_prompt = (
            "You are a professional literary analyst specializing in character "
            "extraction from Chinese web novels. Always respond with valid JSON."
        )

        user_prompt = self.render_prompt(
            self.load_prompt("character_extraction"),
            user_content=chunk,
            chunk_info=f"这是第 {chunk_index}/{total_chunks} 个文本块。",
        )

        try:
            result = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return self._parse_characters(result)
        except Exception as e:
            self.logger.warning(f"第 {chunk_index} 块角色提取失败: {e}")
            return CharacterList()

    def _parse_characters(self, data: dict) -> CharacterList:
        """解析 LLM 返回的 JSON 为 CharacterList。

        容错处理：字段缺失或格式异常时跳过该角色，不中断整体流程。
        """
        characters = []
        for char_data in data.get("characters", []):
            try:
                name = char_data.get("name", "").strip()
                if not name:
                    continue

                # 解析角色定位
                role_str = char_data.get("role", "minor").lower()
                try:
                    role = CharacterRole(role_str)
                except ValueError:
                    role = CharacterRole.MINOR

                # 解析关系（容错）
                relations = []
                for r in char_data.get("relations", []):
                    try:
                        relations.append(CharacterRelation(
                            target=r.get("target", ""),
                            relation=r.get("relation", ""),
                            description=r.get("description", ""),
                        ))
                    except Exception:
                        continue

                character = Character(
                    name=name,
                    english_name=char_data.get("english_name", ""),
                    aliases=char_data.get("aliases", []),
                    gender=char_data.get("gender", ""),
                    age=char_data.get("age", ""),
                    role=role,
                    importance=char_data.get("importance", 0),
                    first_appearance=char_data.get("first_appearance", 0),
                    appearance=char_data.get("appearance", ""),
                    personality=char_data.get("personality", ""),
                    background=char_data.get("background", ""),
                    voice_tone=char_data.get("voice_tone", ""),
                    relations=relations,
                )
                characters.append(character)
            except Exception as e:
                self.logger.debug(f"跳过角色 {char_data.get('name', '?')}: {e}")
                continue

        return CharacterList(characters=characters)

    def _post_process(self, character_list: CharacterList) -> CharacterList:
        """后处理：修正角色定位、补充缺失信息。"""
        for c in character_list.characters:
            # 如果未指定角色定位，根据重要度自动判断
            if c.role == CharacterRole.MINOR and c.importance > 0:
                c.role = _infer_role(c.importance)

            # 如果有关系但目标角色不在列表中，保留关系但标记
            known_names = {ch.name for ch in character_list.characters}
            for r in c.relations:
                if r.target not in known_names:
                    # 尝试通过别名匹配
                    matched = character_list.find_by_name(r.target)
                    if matched:
                        r.target = matched.name  # 规范化为正式名

        # 按重要度降序排列
        character_list.characters.sort(key=lambda c: c.importance, reverse=True)
        return character_list

    def export_character_cards(
        self, character_list: CharacterList, output_dir: Path
    ) -> Path:
        """导出角色卡片为 Markdown 文件。

        Args:
            character_list: 角色列表。
            output_dir: 输出目录。

        Returns:
            输出文件路径。
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "character.md"
        content = character_list.to_markdown()
        output_path.write_text(content, encoding="utf-8")
        self.logger.info(f"角色卡片已导出: {output_path}")
        return output_path


def _importance_to_role(importance: int) -> CharacterRole:
    """根据重要度推断角色定位（旧版兼容）。"""
    return _infer_role(importance)


def _infer_role(importance: int) -> CharacterRole:
    """根据重要度评分推断角色定位。"""
    if importance >= 8:
        return CharacterRole.PROTAGONIST
    elif importance >= 6:
        return CharacterRole.SUPPORTING
    elif importance >= 4:
        return CharacterRole.MINOR
    else:
        return CharacterRole.MENTIONED
=======
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
>>>>>>> main
