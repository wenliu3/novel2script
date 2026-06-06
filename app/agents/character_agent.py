"""角色分析 Agent。

从章节文本中智能提取、分析、合并角色信息，构建完整的角色图谱。
支持两种分析模式：
1. 逐章增量分析（推荐）：每章单独调用 LLM，跨章合并
2. 批量分析：合并文本后分块处理

输出完整的 CharacterAnalysisResult，包含角色列表、关系图谱和各章出场信息。
"""

from __future__ import annotations

import copy
import re
import logging
from pathlib import Path

from app.agents.base_agent import BaseAgent
from app.schema.character import (
    Character,
    CharacterAnalysisResult,
    CharacterGraph,
    CharacterList,
    CharacterRelation,
    CharacterRole,
    ChapterCharacterAppearance,
    build_relation_graph,
)
from app.schema.chapter import Chapter
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# 单次 LLM 调用的最大文本长度
CHUNK_SIZE = 8000

# 角色重要度阈值
IMPORTANCE_THRESHOLD = 3


class CharacterAgent(BaseAgent):
    """角色分析 Agent。

    完整流程：
    1. 逐章或分批调用 LLM 提取角色信息
    2. 跨章/跨批次合并同名角色（别名匹配、信息补充）
    3. 评估角色重要度、标注角色定位
    4. 构建角色关系图谱
    5. 记录各章角色出场信息
    6. 输出 CharacterAnalysisResult

    Attributes:
        name: Agent 名称。
        llm: LLM 服务实例。
        chunk_size: 单次处理的最大文本长度。
        min_importance: 最低重要度阈值。
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
    ) -> CharacterAnalysisResult:
        """执行角色分析。

        优先使用逐章分析模式（传入 chapters），否则使用批量模式。

        Args:
            chapters_text: 待分析的章节文本（批量模式用）。
            chapters: 章节对象列表（逐章模式用，推荐）。
            existing_characters: 已有的角色列表。

        Returns:
            完整的角色分析结果。
        """
        if chapters:
            return self._analyze_by_chapters(chapters, existing_characters)
        return self._analyze_bulk(chapters_text, existing_characters)

    def run(
        self,
        chapters_text: str = "",
        chapters: list[Chapter] | None = None,
        existing_characters: CharacterList | None = None,
    ) -> CharacterAnalysisResult:
        """兼容 orchestrator 调用的 run 方法（委托给 execute）。"""
        return self.execute(chapters_text, chapters, existing_characters)

    # ──────────────────────────────────────────────
    # 逐章增量分析（推荐）
    # ──────────────────────────────────────────────

    def _analyze_by_chapters(
        self,
        chapters: list[Chapter],
        existing_characters: CharacterList | None = None,
    ) -> CharacterAnalysisResult:
        """逐章分析角色，跨章合并。"""
        self.logger.info(f"开始逐章角色分析: {len(chapters)} 个章节")

        aggregated = (
            copy.deepcopy(existing_characters)
            if existing_characters
            else CharacterList()
        )
        chapter_appearances: list[ChapterCharacterAppearance] = []

        for ch in chapters:
            self.logger.info(f"  分析第{ch.number}章...")

            # 调用 LLM 提取本章角色
            chapter_chars = self._extract_from_text(ch.raw_text)

            # 记录出场信息
            appearance = ChapterCharacterAppearance(
                chapter_number=ch.number,
                chapter_title=ch.title,
                characters=[c.name for c in chapter_chars.characters],
            )
            chapter_appearances.append(appearance)

            # 跨章合并
            aggregated = aggregated.merge(chapter_chars)

        # 后处理
        aggregated = self._post_process(aggregated)

        # 构建关系图谱
        graph = build_relation_graph(aggregated)

        result = CharacterAnalysisResult(
            character_list=aggregated,
            relation_graph=graph,
            chapter_appearances=chapter_appearances,
            total_chapters=len(chapters),
        )

        self.logger.info(
            f"角色分析完成: {len(aggregated.characters)} 个角色, "
            f"{len(graph.edges)} 条关系"
        )
        return result

    # ──────────────────────────────────────────────
    # 批量分析（备选）
    # ──────────────────────────────────────────────

    def _analyze_bulk(
        self,
        text: str,
        existing_characters: CharacterList | None = None,
    ) -> CharacterAnalysisResult:
        """批量模式：分块提取后合并。"""
        self.logger.info(f"开始批量角色分析 ({len(text):,} 字符)")

        chunks = self._split_into_chunks(text)
        self.logger.info(f"分为 {len(chunks)} 个文本块")

        all_characters = CharacterList()
        for i, chunk in enumerate(chunks):
            self.logger.info(f"  分析第 {i+1}/{len(chunks)} 块...")
            chunk_chars = self._extract_from_text(chunk)
            all_characters = all_characters.merge(chunk_chars)

        if existing_characters and existing_characters.characters:
            all_characters = existing_characters.merge(all_characters)

        all_characters = self._post_process(all_characters)

        graph = build_relation_graph(all_characters)

        return CharacterAnalysisResult(
            character_list=all_characters,
            relation_graph=graph,
            total_chapters=0,
        )

    # ──────────────────────────────────────────────
    # LLM 调用与解析
    # ──────────────────────────────────────────────

    def _extract_from_text(self, text: str) -> CharacterList:
        """从文本中提取角色信息（单次 LLM 调用）。"""
        truncated = text[:self.chunk_size] if len(text) > self.chunk_size else text

        system_prompt = (
            "You are a professional literary analyst specializing in character "
            "extraction from Chinese web novels. Always respond with valid JSON."
        )
        user_prompt = self.render_prompt(
            self.load_prompt("character_extraction"),
            user_content=truncated,
            chunk_info="",
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
            self.logger.warning(f"角色提取失败: {e}")
            return CharacterList()

    def _parse_characters(self, data: dict) -> CharacterList:
        """解析 LLM 返回的 JSON 为 CharacterList。"""
        characters = []
        for char_data in data.get("characters", []):
            try:
                name = char_data.get("name", "").strip()
                if not name:
                    continue

                role_str = char_data.get("role", "minor").lower()
                try:
                    role = CharacterRole(role_str)
                except ValueError:
                    role = CharacterRole.MINOR

                relations = []
                for r in char_data.get("relations", []):
                    try:
                        relations.append(CharacterRelation(
                            target=r.get("target", ""),
                            relation=r.get("relation", ""),
                            description=r.get("description", ""),
                            strength=r.get("strength", 5),
                            direction=r.get("direction", "双向"),
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

    # ──────────────────────────────────────────────
    # 文本切分
    # ──────────────────────────────────────────────

    def _split_into_chunks(self, text: str) -> list[str]:
        """将长文本按边界切分为多个块。"""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        sections = re.split(r"\n===\s*第?\d+章\s*===\n", text)

        current = ""
        for section in sections:
            if len(current) + len(section) <= self.chunk_size:
                current += ("\n\n" if current else "") + section
            else:
                if current:
                    chunks.append(current)
                if len(section) > self.chunk_size:
                    chunks.extend(self._split_by_paragraphs(section))
                    current = ""
                else:
                    current = section

        if current:
            chunks.append(current)
        return chunks if chunks else [text[:self.chunk_size]]

    def _split_by_paragraphs(self, text: str) -> list[str]:
        paragraphs = text.split("\n\n")
        chunks, current = [], ""
        for para in paragraphs:
            if len(current) + len(para) <= self.chunk_size:
                current += ("\n\n" if current else "") + para
            else:
                if current:
                    chunks.append(current)
                if len(para) > self.chunk_size:
                    chunks.extend(self._split_by_sentences(para))
                    current = ""
                else:
                    current = para
        if current:
            chunks.append(current)
        return chunks

    def _split_by_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[。！？\.\!\?])\s*", text)
        chunks, current = [], ""
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

    # ──────────────────────────────────────────────
    # 后处理
    # ──────────────────────────────────────────────

    def _post_process(self, character_list: CharacterList) -> CharacterList:
        """后处理：修正角色定位、规范化关系目标名。"""
        known_names = {c.name for c in character_list.characters}

        for c in character_list.characters:
            for r in c.relations:
                if r.target not in known_names:
                    matched = character_list.find_by_name(r.target)
                    if matched:
                        r.target = matched.name

        character_list.characters.sort(key=lambda c: c.importance, reverse=True)
        return character_list

    def export_character_cards(
        self, character_list: CharacterList, output_dir: Path
    ) -> Path:
        """导出角色卡片为 Markdown 文件。"""
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "character.md"
        output_path.write_text(character_list.to_markdown(), encoding="utf-8")
        self.logger.info(f"角色卡片已导出: {output_path}")
        return output_path

    def get_character_summary(self, result: CharacterAnalysisResult) -> dict:
        """获取角色分析摘要。"""
        cl = result.character_list
        graph = result.relation_graph
        return {
            "total_characters": len(cl.characters),
            "total_relationships": len(graph.edges),
            "protagonists": len(cl.get_protagonists()),
            "main_characters": len(cl.get_main_characters()),
        }


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
