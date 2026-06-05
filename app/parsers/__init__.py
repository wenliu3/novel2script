"""文件解析模块。

提供中文网络小说的文件读取、编码检测、章节切分等能力。

核心接口：
- parse_novel(novel_dir): 解析小说目录（推荐入口）
- parse_single_file(file_path): 解析单个小说文件
- parse_text_content(text): 解析文本内容
- detect_encoding(file_path): 自动检测文件编码
- read_with_auto_encoding(file_path): 自动编码读取
- split_novel_file(file_path): 切分单文件为多章节

使用示例：
    from app.parsers import parse_novel
    from pathlib import Path

    info = parse_novel(Path("novels/诡秘之主"))
    print(f"共 {info.chapter_count} 章, {info.total_chars} 字")
"""

from app.parsers.novel_parser import (
    NovelInfo,
    parse_novel,
    parse_single_file,
    parse_text_content,
)
from app.parsers.encoding_detector import (
    detect_encoding,
    read_with_auto_encoding,
)
from app.parsers.chapter_splitter import (
    split_novel_file,
    split_text_by_chapters,
    extract_chapter_number,
    SplitResult,
)
from app.parsers.chapter_parser import (
    split_paragraphs,
    extract_dialogue,
    clean_text,
)

__all__ = [
    # 顶层入口
    "parse_novel",
    "parse_single_file",
    "parse_text_content",
    "NovelInfo",
    # 编码检测
    "detect_encoding",
    "read_with_auto_encoding",
    # 章节切分
    "split_novel_file",
    "split_text_by_chapters",
    "extract_chapter_number",
    "SplitResult",
    # 文本解析
    "split_paragraphs",
    "extract_dialogue",
    "clean_text",
]
