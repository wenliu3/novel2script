"""小说文件解析器（顶层入口）。

负责扫描小说目录结构、协调编码检测和章节切分，
输出标准化的输入数据供 Agent 流水线使用。

支持两种输入模式：
1. 目录模式：novels/{小说名}/origin/ 下每章一个 .txt 文件
2. 单文件模式：一个 .txt 文件包含整本小说
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.parsers.chapter_parser import clean_text
from app.parsers.chapter_splitter import SplitResult, split_novel_file
from app.parsers.encoding_detector import detect_encoding, read_with_auto_encoding
from app.schema.chapter import Chapter

logger = logging.getLogger(__name__)


@dataclass
class NovelInfo:
    """小说解析结果。"""

    name: str = ""
    novel_dir: Path = field(default_factory=lambda: Path("."))
    chapters: list[Chapter] = field(default_factory=list)
    total_chars: int = 0
    has_character_file: bool = False
    has_overview_file: bool = False
    character_content: str = ""
    overview_content: str = ""
    parse_mode: str = ""  # "directory" 或 "single_file"
    encoding_summary: dict[str, int] = field(default_factory=dict)  # {编码: 文件数}

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)

    @property
    def avg_chapter_length(self) -> float:
        if not self.chapters:
            return 0.0
        return self.total_chars / len(self.chapters)

    def summary(self) -> str:
        parts = [
            f"小说: {self.name}",
            f"章节数: {self.chapter_count}",
            f"总字数: {self.total_chars:,}",
            f"平均章长: {self.avg_chapter_length:,.0f} 字",
            f"解析模式: {self.parse_mode}",
        ]
        if self.encoding_summary:
            enc_str = ", ".join(f"{k}: {v}个文件" for k, v in self.encoding_summary.items())
            parts.append(f"编码分布: {enc_str}")
        if self.has_character_file:
            parts.append("角色关系: ✓")
        if self.has_overview_file:
            parts.append("故事概览: ✓")
        return "\n".join(parts)


def parse_novel(novel_dir: Path) -> NovelInfo:
    """解析小说目录，输出结构化数据。

    目录结构约定：
        novels/
          └── {novel_name}/
                ├── character.md   # 角色关系（可选）
                ├── overview.md    # 故事概览（可选）
                └── origin/
                      ├── 001.txt  # 单章文件模式
                      ├── 002.txt
                      └── ...
                  或
                      └── full.txt # 整本小说单文件模式

    Args:
        novel_dir: 小说根目录。

    Returns:
        解析结果。

    Raises:
        FileNotFoundError: 目录不存在或结构不符合约定时抛出。
    """
    if not novel_dir.exists():
        raise FileNotFoundError(f"小说目录不存在: {novel_dir}")

    info = NovelInfo(
        name=novel_dir.name,
        novel_dir=novel_dir,
    )

    # ── 读取可选的元数据文件 ──
    _read_metadata_files(info)

    # ── 检测解析模式 ──
    origin_dir = novel_dir / "origin"
    if not origin_dir.exists():
        raise FileNotFoundError(
            f"章节目录不存在: {origin_dir}\n"
            f"请在 {novel_dir} 下创建 origin/ 目录并放入章节文件"
        )

    txt_files = list(origin_dir.glob("*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"origin/ 目录下没有 .txt 文件: {origin_dir}")

    # ── 判断模式并解析 ──
    if len(txt_files) == 1 and txt_files[0].stat().st_size > 100_000:
        # 单个大文件 → 可能是整本小说，尝试切分
        info = _parse_single_file(txt_files[0], info)
        info.parse_mode = "single_file"
    else:
        # 多个文件 → 每个文件对应一章
        info = _parse_directory(txt_files, info)
        info.parse_mode = "directory"

    logger.info(f"\n{info.summary()}")
    return info


def parse_single_file(file_path: Path) -> NovelInfo:
    """直接解析单个小说文件。

    不需要目录结构，直接传入一个 .txt 文件路径。

    Args:
        file_path: 小说文件路径。

    Returns:
        解析结果。
    """
    info = NovelInfo(
        name=file_path.stem,
        novel_dir=file_path.parent,
        parse_mode="single_file",
    )
    info = _parse_single_file(file_path, info)
    logger.info(f"\n{info.summary()}")
    return info


def parse_text_content(
    text: str,
    title: str = "未知小说",
    source_label: str = "",
) -> NovelInfo:
    """直接解析文本内容（不依赖文件系统）。

    用于处理从 API、剪贴板等来源获取的文本。

    Args:
        text: 小说文本内容。
        title: 小说标题。
        source_label: 来源标识。

    Returns:
        解析结果。
    """
    from app.parsers.chapter_splitter import split_text_by_chapters

    info = NovelInfo(name=title, parse_mode="text_content")
    result = split_text_by_chapters(text, source_label=source_label)

    info.chapters = result.chapters
    info.total_chars = result.total_chars

    logger.info(f"\n{info.summary()}")
    return info


# ── 内部函数 ──


def _parse_single_file(file_path: Path, info: NovelInfo) -> NovelInfo:
    """解析单个小说文件。"""
    result = split_novel_file(file_path)
    info.chapters = result.chapters
    info.total_chars = result.total_chars
    encoding = detect_encoding(file_path)
    info.encoding_summary[encoding] = 1
    return info


def _parse_directory(txt_files: list[Path], info: NovelInfo) -> NovelInfo:
    """解析目录下的多个章节文件。"""
    encoding_counts: dict[str, int] = {}
    chapters = []

    for filepath in sorted(txt_files):
        try:
            encoding, content = read_with_auto_encoding(filepath)

            # 记录编码统计
            encoding_counts[encoding] = encoding_counts.get(encoding, 0) + 1

            # 从文件名提取章节编号
            numbers = re.findall(r"\d+", filepath.stem)
            chapter_num = int(numbers[-1]) if numbers else len(chapters) + 1

            # 尝试提取标题
            title = _extract_title_from_text(content)

            cleaned = clean_text(content)

            chapter = Chapter(
                number=chapter_num,
                title=title,
                raw_text=cleaned,
                original_text=content,
                file_path=str(filepath),
                encoding=encoding,
            )
            chapters.append(chapter)

        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"跳过文件 {filepath.name}: {e}")

    # 按章节编号排序
    chapters.sort(key=lambda ch: ch.number)
    info.chapters = chapters
    info.total_chars = sum(ch.word_count for ch in chapters)
    info.encoding_summary = encoding_counts

    return info


def _read_metadata_files(info: NovelInfo) -> None:
    """读取可选的元数据文件（character.md, overview.md）。"""
    char_file = info.novel_dir / "character.md"
    if char_file.exists():
        try:
            info.character_content = char_file.read_text(encoding="utf-8").strip()
            info.has_character_file = bool(info.character_content)
        except Exception as e:
            logger.warning(f"读取 character.md 失败: {e}")

    overview_file = info.novel_dir / "overview.md"
    if overview_file.exists():
        try:
            info.overview_content = overview_file.read_text(encoding="utf-8").strip()
            info.has_overview_file = bool(info.overview_content)
        except Exception as e:
            logger.warning(f"读取 overview.md 失败: {e}")


def _extract_title_from_text(text: str) -> str:
    """从文本开头提取章节标题（内联实现，避免循环导入）。"""
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
        if len(line) < 50:
            return line
    return ""
