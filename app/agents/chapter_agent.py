"""章节解析与分析 Agent（PR-03 核心模块）。

负责两阶段工作：
1. 文件解析阶段：扫描小说目录、识别章节文件、解析章节文本
2. LLM 分析阶段：逐章调用 LLM 生成摘要、提取关键事件、识别角色和场景

输出结构化的 Chapter 和 ChapterAnalysis 数据，
为下游 CharacterAgent、SceneAgent 提供标准化输入。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.agents.base_agent import BaseAgent
from app.schema.chapter import (
    Chapter,
    ChapterAnalysis,
    ChapterAnalysisReport,
    KeyEvent,
)
from app.services.llm_service import LLMService
from app.parsers.encoding_detector import read_with_auto_encoding

# 单章最大分析长度（字符数），超出则截断
MAX_CHAPTER_LENGTH = 12000


class ChapterAgent(BaseAgent):
    """章节解析与分析 Agent。

    职责：
    1. 扫描 origin/ 目录获取章节文件列表
    2. 按编号排序并解析每章内容
    3. 调用 LLM 对每章进行深度分析：
       - 生成章节摘要
       - 提取关键事件
       - 识别出场角色
       - 识别地点/场景线索
       - 分析情感基调
    4. 汇总分析结果，生成 ChapterAnalysisReport
    """

    def __init__(self, llm: LLMService) -> None:
        super().__init__("chapter_agent", llm)

    # ── 第一阶段：文件解析 ──

    def execute(self, novel_dir: Path) -> list[Chapter]:
        """解析小说章节文件（文件级操作，不使用 LLM）。

        Args:
            novel_dir: 小说根目录（包含 origin/ 子目录）。

        Returns:
            按编号排序的 Chapter 列表。

        Raises:
            FileNotFoundError: 章节目录不存在时抛出。
        """
        origin_dir = novel_dir / "origin"
        if not origin_dir.exists():
            raise FileNotFoundError(f"章节目录不存在: {origin_dir}")

        # 扫描章节文件
        chapter_files = self._scan_chapters(origin_dir)
        self.logger.info(f"发现 {len(chapter_files)} 个章节文件")

        # 解析每章
        chapters = []
        for num, filepath in sorted(chapter_files.items()):
            try:
                encoding, raw_text = read_with_auto_encoding(filepath)
                chapter = Chapter(
                    number=num,
                    title=self._extract_title(raw_text),
                    raw_text=raw_text,
                    file_path=str(filepath),
                    encoding=encoding,
                )
                chapters.append(chapter)
                self.logger.debug(f"  第{num}章: {chapter.word_count} 字")
            except (FileNotFoundError, ValueError) as e:
                self.logger.warning(f"  跳过第{num}章: {e}")

        self.logger.info(f"成功解析 {len(chapters)} 个章节")
        return chapters

    # ── 第二阶段：LLM 章节分析 ──

    def analyze_chapter(self, chapter: Chapter) -> ChapterAnalysis:
        """对单个章节进行 LLM 深度分析。

        Args:
            chapter: 已解析的章节对象。

        Returns:
            章节分析结果，包含摘要、关键事件、角色、地点等。
        """
        self.logger.info(f"  LLM 分析第{chapter.number}章: {chapter.title}")

        text = chapter.raw_text or ""
        if not text.strip():
            self.logger.warning(f"  第{chapter.number}章文本为空，跳过 LLM 分析")
            return ChapterAnalysis(
                chapter_number=chapter.number,
                chapter_title=chapter.title or f"第{chapter.number}章",
                word_count=0,
            )

        # 截断过长文本
        truncated = text[:MAX_CHAPTER_LENGTH] if len(text) > MAX_CHAPTER_LENGTH else text
        if len(text) > MAX_CHAPTER_LENGTH:
            self.logger.debug(f"  第{chapter.number}章文本过长，截断至 {MAX_CHAPTER_LENGTH} 字符")

        try:
            result = self.llm_prompt_json("chapter_extraction", truncated)
            analysis = self._parse_analysis(result, chapter, len(text))
            self.logger.info(
                f"  ✓ 第{chapter.number}章分析完成: "
                f"{analysis.event_count} 个事件, "
                f"{len(analysis.characters_seen)} 个角色, "
                f"{len(analysis.location_hints)} 个地点"
            )
            return analysis
        except Exception as e:
            self.logger.error(f"  ✗ 第{chapter.number}章 LLM 分析失败: {e}")
            # 返回不带 LLM 结果的基本分析
            return ChapterAnalysis(
                chapter_number=chapter.number,
                chapter_title=chapter.title or f"第{chapter.number}章",
                word_count=len(text),
            )

    def analyze_chapters(
        self,
        chapters: list[Chapter],
    ) -> ChapterAnalysisReport:
        """逐章分析所有章节，汇总结果。

        这是 PR-03 的核心入口方法。

        Args:
            chapters: 已解析的章节列表。

        Returns:
            包含所有章节分析结果和汇总信息的报告。
        """
        if not chapters:
            self.logger.warning("没有要分析的章节")
            return ChapterAnalysisReport()

        self.logger.info(f"开始逐章分析: {len(chapters)} 个章节")
        analyses: list[ChapterAnalysis] = []
        all_chars_set: set[str] = set()
        all_locs_set: set[str] = set()
        total_events = 0

        for chapter in chapters:
            analysis = self.analyze_chapter(chapter)
            analyses.append(analysis)

            # 收集汇总数据
            all_chars_set.update(
                name.replace(" [新]", "") for name in analysis.characters_seen
            )
            all_locs_set.update(analysis.location_hints)
            total_events += analysis.event_count

        report = ChapterAnalysisReport(
            analyses=analyses,
            total_chapters=len(chapters),
            total_events=total_events,
            all_characters=sorted(all_chars_set),
            all_locations=sorted(all_locs_set),
        )

        self.logger.info(
            f"章节分析汇总: {report.total_chapters} 章, "
            f"{report.total_events} 个事件, "
            f"{len(report.all_characters)} 个不同角色, "
            f"{len(report.all_locations)} 个地点"
        )

        return report

    def run_full_pipeline(self, novel_dir: Path) -> tuple[list[Chapter], ChapterAnalysisReport]:
        """运行完整流水线：解析 + 分析。

        便捷方法，一次性完成文件解析和 LLM 分析。

        Args:
            novel_dir: 小说根目录。

        Returns:
            (章节列表, 分析报告) 元组。
        """
        chapters = self.execute(novel_dir)
        report = self.analyze_chapters(chapters)
        return chapters, report

    # ── 内部方法 ──

    def _parse_analysis(
        self,
        result: dict[str, Any],
        chapter: Chapter,
        word_count: int,
    ) -> ChapterAnalysis:
        """从 LLM JSON 响应解析 ChapterAnalysis 对象。

        Args:
            result: LLM 返回的 JSON 字典。
            chapter: 原始章节对象。
            word_count: 章节实际字数。

        Returns:
            解析后的 ChapterAnalysis 对象。
        """
        key_events = []
        for evt in result.get("key_events", []):
            key_events.append(
                KeyEvent(
                    event_id=evt.get("event_id", ""),
                    description=evt.get("description", ""),
                    participants=evt.get("participants", []),
                    location=evt.get("location", ""),
                    importance=evt.get("importance", "minor"),
                    start_hint=evt.get("start_hint", ""),
                )
            )

        return ChapterAnalysis(
            chapter_number=result.get("chapter_number", chapter.number),
            chapter_title=result.get("chapter_title", chapter.title),
            summary=result.get("summary", ""),
            key_events=key_events,
            characters_seen=result.get("characters_seen", []),
            location_hints=result.get("location_hints", []),
            emotion_tone=result.get("emotion_tone", ""),
            word_count=word_count,
        )

    def _scan_chapters(self, origin_dir: Path) -> dict[int, Path]:
        """扫描目录，返回 {章节编号: 文件路径} 映射。"""
        chapters = {}
        for f in sorted(origin_dir.iterdir()):
            if f.is_file() and f.suffix == ".txt":
                numbers = re.findall(r"\d+", f.stem)
                if numbers:
                    chapters[int(numbers[-1])] = f
        return chapters

    def _extract_title(self, text: str) -> str:
        """尝试从文本开头提取章节标题。

        匹配常见格式：
        - "第X章 标题"
        - "Chapter X: Title"
        - 第一行非空文本
        """
        lines = text.strip().split("\n")
        for line in lines[:5]:
            line = line.strip()
            if not line:
                continue
            # 中文章节标题
            match = re.match(r"第[一二三四五六七八九十百千\d]+章\s*(.*)", line)
            if match:
                return match.group(1).strip() or line
            # 英文章节标题
            match = re.match(r"Chapter\s+\d+[:\s]*(.*)", line, re.IGNORECASE)
            if match:
                return match.group(1).strip() or line
            # 其他：如果行不长，可能是标题
            if len(line) < 50:
                return line
        return ""
