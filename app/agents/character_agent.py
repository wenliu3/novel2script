"""人物分析 Agent。

从章节文本中智能提取、分析、合并角色信息，构建完整的角色图谱。
支持长文本分批处理、跨章节角色合并、重要度排序、关系图谱构建。
"""

import re
import logging
from pathlib import Path

from app.agents.base_agent import BaseAgent
from app.schema.character import Character, CharacterList, CharacterRelation, CharacterRole
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# 单次 LLM 调用的最大文本长度（留足上下文空间给提示词和输出）
CHUNK_SIZE = 8000

# 角色重要度阈值
IMPORTANCE_THRESHOLD = 3  # 低于此值的角色视为龙套，不进入最终图谱


class CharacterAgent(BaseAgent):
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
        existing_characters: CharacterList | None = None,
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
            all_characters = existing_characters.merge(all_characters)
            self.logger.info(f"与已有角色合并后: {len(all_characters.characters)} 个角色")

        # ── Step 3: 后处理 ──
        all_characters = self._post_process(all_characters)

        # ── Step 4: 过滤低重要度角色 ──
        filtered = CharacterList(
            characters=[
                c for c in all_characters.characters
                if c.importance >= self.min_importance
            ]
        )

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
