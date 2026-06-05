"""章节解析 Agent。

负责读取小说章节目录、解析章节文本，输出结构化的 Chapter 数据。
这是流水线的第一个环节，为后续 Agent 提供标准化输入。
"""

import re
from pathlib import Path

from app.agents.base_agent import BaseAgent
from app.schema.chapter import Chapter
from app.services.llm_service import LLMService
from app.parsers.encoding_detector import read_with_auto_encoding


class ChapterAgent(BaseAgent):
    """章节解析 Agent。

    职责：
    1. 扫描 origin/ 目录获取章节文件列表
    2. 按编号排序
    3. 读取并解析每章内容
    4. 输出标准化的 Chapter 对象列表
    """

    def __init__(self, llm: LLMService) -> None:
        super().__init__("chapter_agent", llm)

    def execute(self, novel_dir: Path) -> list[Chapter]:
        """解析小说章节。

        Args:
            novel_dir: 小说根目录（包含 origin/ 子目录）。

        Returns:
            按编号排序的 Chapter 列表。
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
