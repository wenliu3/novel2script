"""文本切分器。

合并原 text_splitter.py + encoding_detector.py + chapter_splitter.py。
提供两种切分策略：
1. 按章节切分（正则检测章节标题）
2. 按块切分（递归字符切分，类似 RecursiveCharacterTextSplitter）
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 编码检测
# ═══════════════════════════════════════════════════════════════

COMMON_ENCODINGS = ["utf-8", "utf-8-sig", "gbk", "gb18030", "gb2312", "big5", "latin-1"]


def read_file(path: Path) -> tuple[str, str]:
    """自动检测编码并读取文件。返回 (编码, 文本)。"""
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    raw = path.read_bytes()
    if not raw:
        raise ValueError(f"文件为空: {path}")

    # BOM 检测
    bom_map = [(b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be")]
    for bom, enc in bom_map:
        if raw.startswith(bom):
            return enc, raw.decode(enc).strip()

    # 逐个尝试
    for enc in COMMON_ENCODINGS:
        try:
            text = raw.decode(enc)
            chinese = sum(1 for c in text if "一" <= c <= "鿿")
            if chinese >= len(text) * 0.01 or enc == "latin-1":
                return enc, text.strip()
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(f"无法检测编码: {path}")


def clean_text(text: str) -> str:
    """清理文本：统一换行、去除行尾空白、合并多余空行。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return text.strip()


# ═══════════════════════════════════════════════════════════════
# 文本块
# ═══════════════════════════════════════════════════════════════

@dataclass
class TextChunk:
    """文本块。"""
    index: int
    text: str
    start_char: int = 0
    end_char: int = 0
    is_first: bool = False
    is_last: bool = False
    title: str = ""  # 章节标题（按章节切分时填充）
    chapter_number: int = 0  # 原始章节编号（从标题提取）

    @property
    def length(self) -> int:
        return len(self.text)


# ═══════════════════════════════════════════════════════════════
# 递归字符切分
# ═══════════════════════════════════════════════════════════════

DEFAULT_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]


class TextSplitter:
    """递归字符文本切分器。

    Usage:
        splitter = TextSplitter(chunk_size=100000, chunk_overlap=5000)
        chunks = splitter.split(text)
    """

    def __init__(self, chunk_size: int = 100_000, chunk_overlap: int = 5_000) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError(f"chunk_overlap ({chunk_overlap}) 必须小于 chunk_size ({chunk_size})")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str) -> list[TextChunk]:
        """切分文本。"""
        if not text.strip():
            return []
        if len(text) <= self.chunk_size:
            return [TextChunk(index=0, text=text, is_first=True, is_last=True)]

        raw_chunks = self._recursive_split(text, list(DEFAULT_SEPARATORS))
        merged = self._merge_small(raw_chunks)
        chunks = self._add_overlap(merged)
        if chunks:
            chunks[0].is_first = True
            chunks[-1].is_last = True
        logger.info(f"切分完成: {len(text):,} 字符 → {len(chunks)} 块")
        return chunks

    def _recursive_split(self, text: str, seps: list[str]) -> list[str]:
        if not seps:
            return self._force_split(text)
        sep = seps[0]
        rest = seps[1:]
        parts = text.split(sep) if sep else self._force_split(text)
        merged, current = [], ""
        for part in parts:
            piece = part + sep if sep and part else part
            if len(current + piece) <= self.chunk_size:
                current += piece
            else:
                if current:
                    merged.append(current.rstrip(sep) if sep else current)
                if len(part) > self.chunk_size:
                    merged.extend(self._recursive_split(part, rest))
                    current = ""
                else:
                    current = piece
        if current.strip():
            merged.append(current.rstrip(sep) if sep else current)
        return [m for m in merged if m.strip()]

    def _force_split(self, text: str) -> list[str]:
        chunks, start = [], 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - self.chunk_overlap if end < len(text) else end
        return chunks

    def _merge_small(self, chunks: list[str]) -> list[str]:
        if not chunks:
            return []
        merged, current = [], chunks[0]
        for chunk in chunks[1:]:
            if len(current + chunk) <= self.chunk_size:
                current += chunk
            else:
                merged.append(current)
                current = chunk
        if current:
            merged.append(current)
        return merged

    def _add_overlap(self, chunks: list[str]) -> list[TextChunk]:
        result, pos = [], 0
        for i, chunk in enumerate(chunks):
            if i > 0 and self.chunk_overlap > 0:
                prev_tail = chunks[i - 1][-self.chunk_overlap:]
                for s in ["\n\n", "\n", "。"]:
                    idx = prev_tail.find(s)
                    if idx > 0:
                        prev_tail = prev_tail[idx + len(s):]
                        break
                chunk = prev_tail + chunk
            result.append(TextChunk(index=i, text=chunk, start_char=pos, end_char=pos + len(chunks[i])))
            pos += len(chunks[i])
        return result


# ═══════════════════════════════════════════════════════════════
# 章节检测
# ═══════════════════════════════════════════════════════════════

CHAPTER_PATTERNS = [
    (re.compile(r"第[一二三四五六七八九十百千万零\d]+[章节回折幕集篇部][　\s:：]*(.*)", re.MULTILINE), 0.9),
    (re.compile(r"(?:Chapter|Part|Episode|Section)\s+\d+[:\s]*(.*)", re.MULTILINE | re.IGNORECASE), 0.85),
    (re.compile(r"^[　\s]*(楔子|序章|序|前言|引子|尾声|终章|番外)[　\s:：]*(.*)", re.MULTILINE), 0.85),
]


def has_chapter_structure(text: str) -> bool:
    """检测文本是否有章节结构（至少 2 个高置信度标题）。"""
    count = 0
    for pattern, _ in CHAPTER_PATTERNS:
        count += len(pattern.findall(text))
        if count >= 2:
            return True
    return False


# 中文数字 → 阿拉伯数字映射
_CN_NUM_MAP = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "百": 100, "千": 1000, "万": 10000,
}


def _extract_chapter_number(heading: str) -> int:
    """从章节标题中提取章节编号。"""
    # 阿拉伯数字: 第001章, 第1回
    m = re.search(r"第\s*(\d+)", heading)
    if m:
        return int(m.group(1))
    # 中文数字: 第一章, 第二回
    m = re.search(r"第([一二三四五六七八九十百千万零\d]+)", heading)
    if m:
        cn_str = m.group(1)
        if cn_str.isdigit():
            return int(cn_str)
        result, current = 0, 0
        for char in cn_str:
            if char in _CN_NUM_MAP:
                val = _CN_NUM_MAP[char]
                if val >= 10:
                    if current == 0:
                        current = 1
                    result += current * val
                    current = 0
                else:
                    current = current * 10 + val
            elif char.isdigit():
                current = current * 10 + int(char)
        return result + current
    return 0


def split_by_chapters(text: str) -> list[tuple[int, str, str]]:
    """按章节切分文本。返回 [(章节编号, 标题, 内容), ...]。"""
    for pattern, _ in CHAPTER_PATTERNS:
        matches = list(pattern.finditer(text))
        if len(matches) >= 2:
            chapters: list[tuple[int, str, str]] = []
            for i, match in enumerate(matches):
                full_heading = match.group(0).strip()
                title = match.group(1).strip() if match.lastindex else full_heading
                chapter_num = _extract_chapter_number(full_heading)
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                content = text[start:end].strip()
                if content:
                    chapters.append((chapter_num, title, content))
            if chapters:
                return chapters
    return []


# ═══════════════════════════════════════════════════════════════
# 智能切分入口
# ═══════════════════════════════════════════════════════════════

def smart_split(text: str, chunk_size: int = 100_000, chunk_overlap: int = 0) -> list[TextChunk]:
    """智能切分：先尝试按章节切，超长章节再按块切。

    Args:
        text: 完整文本。
        chunk_size: 每块目标大小。
        chunk_overlap: 重叠大小（0 表示自动取 chunk_size 的 5%）。

    Returns:
        TextChunk 列表。
    """
    if chunk_overlap <= 0:
        chunk_overlap = max(500, chunk_size // 20)  # 5%，最少 500
    if chunk_overlap >= chunk_size:
        chunk_overlap = chunk_size // 4
    splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    if has_chapter_structure(text):
        chapters = split_by_chapters(text)
        if len(chapters) >= 2:
            logger.info(f"检测到 {len(chapters)} 个章节")
            chunks = []
            for chapter_num, title, content in chapters:
                if len(content) > chunk_size:
                    sub_chunks = splitter.split(content)
                    for sc in sub_chunks:
                        sc.title = title
                        sc.chapter_number = chapter_num
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(TextChunk(
                        index=len(chunks), text=content,
                        title=title, chapter_number=chapter_num,
                    ))
            if chunks:
                chunks[0].is_first = True
                chunks[-1].is_last = True
                for i, c in enumerate(chunks):
                    c.index = i
            return chunks

    logger.info("无章节结构，按块大小切分")
    return splitter.split(text)
