"""章节切分器。

将单个大文件（包含多个章节的完整小说）切分为独立章节。
支持多种章节标题格式和切分策略。

典型输入：一个包含全本小说的 .txt 文件
输出：按章节编号组织的 Chapter 列表
"""

import re
import logging
from dataclasses import dataclass
from pathlib import Path

from app.parsers.chapter_parser import clean_text
from app.parsers.encoding_detector import read_with_auto_encoding
from app.schema.chapter import Chapter, ChapterMeta

logger = logging.getLogger(__name__)


# ── 章节标题匹配模式（按优先级排列） ──

CHAPTER_PATTERNS: list[re.Pattern] = [
    # 中文数字: 第一章、第二十三回、第一百零五回
    re.compile(
        r"^[　\s]*(?:卷[首一二三四五六七八九十百千\d]*[　\s]*)?"
        r"第[一二三四五六七八九十百千万零\d]+[章节回折幕集篇部]"
        r"[　\s:：]*(.*)",
        re.MULTILINE,
    ),
    # 阿拉伯数字: 第1章、第123节
    re.compile(
        r"^[　\s]*(?:卷\d+[　\s]*)?"
        r"第\d+[章节回折幕集篇部]"
        r"[　\s:：]*(.*)",
        re.MULTILINE,
    ),
    # 英文: Chapter 1, CHAPTER 12
    re.compile(
        r"^[　\s]*Chapter\s+\d+[:\s]*(.*)",
        re.MULTILINE | re.IGNORECASE,
    ),
    # 纯数字行: 1、12、001（作为标题行）
    re.compile(
        r"^[　\s]*(\d{1,4})[　\s]*$",
        re.MULTILINE,
    ),
]


@dataclass
class SplitResult:
    """切分结果。"""

    chapters: list[Chapter]
    total_chars: int
    split_method: str  # 使用的切分模式描述


def split_novel_file(
    file_path: Path,
    chapter_number_offset: int = 0,
) -> SplitResult:
    """将单个小说文件切分为多个章节。

    Args:
        file_path: 小说文件路径。
        chapter_number_offset: 章节编号偏移量（用于多文件合并时保持编号连续）。

    Returns:
        切分结果。
    """
    encoding, full_text = read_with_auto_encoding(file_path)
    logger.info(f"读取文件: {file_path.name} (编码: {encoding}, 字数: {len(full_text)})")

    # 尝试多种切分模式
    for i, pattern in enumerate(CHAPTER_PATTERNS):
        chapters = _split_by_pattern(full_text, pattern, file_path, encoding, chapter_number_offset)
        if chapters and len(chapters) >= 2:
            method_name = _get_pattern_name(i)
            logger.info(f"切分成功: 使用 {method_name}, 得到 {len(chapters)} 个章节")
            total_chars = sum(ch.word_count for ch in chapters)
            return SplitResult(chapters=chapters, total_chars=total_chars, split_method=method_name)

    # 所有模式都失败 → 作为单章返回
    logger.warning(f"未检测到章节标题，将整个文件作为单章处理: {file_path.name}")
    chapter = Chapter(
        number=1 + chapter_number_offset,
        title=file_path.stem,
        raw_text=clean_text(full_text),
        original_text=full_text,
        file_path=str(file_path),
        encoding=encoding,
    )
    return SplitResult(chapters=[chapter], total_chars=len(full_text), split_method="single_chapter")


def split_text_by_chapters(
    text: str,
    source_label: str = "",
    encoding: str = "utf-8",
) -> SplitResult:
    """将文本字符串按章节标题切分。

    用于处理已经读入内存的文本（如来自网络下载或 API 响应）。

    Args:
        text: 待切分的文本。
        source_label: 来源标识（用于日志）。
        encoding: 文本编码标识。

    Returns:
        切分结果。
    """
    for i, pattern in enumerate(CHAPTER_PATTERNS):
        chapters = _split_by_pattern(text, pattern, Path(source_label), encoding, 0)
        if chapters and len(chapters) >= 2:
            method_name = _get_pattern_name(i)
            total_chars = sum(ch.word_count for ch in chapters)
            return SplitResult(chapters=chapters, total_chars=total_chars, split_method=method_name)

    chapter = Chapter(
        number=1,
        title=source_label or "未知章节",
        raw_text=clean_text(text),
        original_text=text,
        file_path=source_label,
        encoding=encoding,
    )
    return SplitResult(chapters=[chapter], total_chars=len(text), split_method="single_chapter")


def extract_chapter_number(title_line: str) -> int | None:
    """从标题行中提取章节编号。

    Args:
        title_line: 章节标题行文本。

    Returns:
        章节编号，无法提取时返回 None。
    """
    # 中文数字映射
    cn_num_map = {
        "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
        "十": 10, "百": 100, "千": 1000, "万": 10000,
    }

    # 阿拉伯数字
    match = re.search(r"第(\d+)", title_line)
    if match:
        return int(match.group(1))

    # 中文数字: 第一章、第二十三回
    match = re.search(r"第([一二三四五六七八九十百千万零\d]+)", title_line)
    if match:
        cn_str = match.group(1)
        # 纯阿拉伯数字（混在中文模式里）
        if cn_str.isdigit():
            return int(cn_str)
        # 中文数字转阿拉伯
        return _cn_to_num(cn_str, cn_num_map)

    # 英文: Chapter 12
    match = re.search(r"Chapter\s+(\d+)", title_line, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def _split_by_pattern(
    text: str,
    pattern: re.Pattern,
    source_path: Path,
    encoding: str,
    number_offset: int,
) -> list[Chapter]:
    """使用指定正则模式切分文本。"""
    # 找到所有匹配位置
    matches = list(pattern.finditer(text))

    if len(matches) < 2:
        return []

    chapters = []
    for i, match in enumerate(matches):
        title_line = match.group(0).strip()
        # 提取标题（去掉编号部分后的文字）
        title = match.group(1).strip() if match.lastindex else title_line
        title = re.sub(r"^[一二三四五六七八九十百千万零\d]+[章节回折幕集篇部][　\s:：]*", "", title).strip()

        # 提取章节编号
        num = extract_chapter_number(title_line)
        if num is None:
            num = i + 1
        num += number_offset

        # 提取章节内容（当前匹配到下一个匹配之间的文本）
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        if not content:
            continue  # 跳过空章节

        cleaned = clean_text(content)
        chapter = Chapter(
            number=num,
            title=title or title_line,
            raw_text=cleaned,
            original_text=content,
            file_path=str(source_path),
            encoding=encoding,
        )
        chapters.append(chapter)

    return chapters


def _cn_to_num(cn_str: str, cn_num_map: dict) -> int:
    """中文数字转阿拉伯数字。

    支持：一～十九, 二十, 三十, 一百, 一千, 一万 等组合。
    """
    if not cn_str:
        return 0

    result = 0
    current = 0

    for char in cn_str:
        if char in cn_num_map:
            val = cn_num_map[char]
            if val >= 10:
                if current == 0:
                    current = 1
                result += current * val
                current = 0
            else:
                current = current * 10 + val
        else:
            current = current * 10 + (ord(char) - ord("零")) if char.isdigit() else 0

    return result + current


def _get_pattern_name(index: int) -> str:
    """获取切分模式的描述名称。"""
    names = [
        "中文章节标题 (第X章/回)",
        "阿拉伯数字标题 (第1章/节)",
        "英文标题 (Chapter N)",
        "纯数字行标题",
    ]
    return names[index] if index < len(names) else f"模式#{index}"
