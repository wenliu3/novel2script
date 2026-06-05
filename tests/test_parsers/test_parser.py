"""文件解析模块测试。

测试编码检测、章节切分、小说目录扫描等核心功能。
"""

import pytest
from pathlib import Path
from app.parsers import (
    detect_encoding,
    read_with_auto_encoding,
    split_text_by_chapters,
    split_novel_file,
    extract_chapter_number,
    parse_text_content,
)
from app.parsers.chapter_parser import split_paragraphs, extract_dialogue, clean_text


# ──────────────────────────────────────
# 编码检测
# ──────────────────────────────────────


class TestEncodingDetector:
    """编码自动检测测试。"""

    def test_detect_utf8(self, tmp_path):
        """UTF-8 文件应被正确识别。"""
        f = tmp_path / "test.txt"
        f.write_text("这是一段中文内容，用于测试编码检测。", encoding="utf-8")
        enc = detect_encoding(f)
        assert enc in ("utf-8", "utf-8-sig")

    def test_detect_gbk(self, tmp_path):
        """GBK 编码文件应被正确识别。"""
        f = tmp_path / "test.txt"
        f.write_bytes("这是一段GBK编码的中文内容。".encode("gbk"))
        enc = detect_encoding(f)
        assert enc in ("gbk", "gb18030", "gb2312")

    def test_read_with_auto_encoding(self, tmp_path):
        """自动读取应返回正确的编码和内容。"""
        f = tmp_path / "test.txt"
        content = "第一章 开始\n\n这是正文内容。"
        f.write_text(content, encoding="utf-8")
        enc, text = read_with_auto_encoding(f)
        assert "第一章 开始" in text
        assert "正文内容" in text

    def test_read_nonexistent_file(self):
        """读取不存在的文件应抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            read_with_auto_encoding(Path("不存在的文件.txt"))

    def test_read_empty_file(self, tmp_path):
        """读取空文件应抛出 ValueError。"""
        f = tmp_path / "empty.txt"
        f.write_text("")
        with pytest.raises(ValueError):
            read_with_auto_encoding(f)


# ──────────────────────────────────────
# 章节切分
# ──────────────────────────────────────


class TestChapterSplitter:
    """章节切分器测试。"""

    SAMPLE_TEXT = """第一章 初入江湖

少年站在山巅，望着远方的城镇，心中充满了期待。

这是他第一次下山，师父说外面的世界很危险。

第二章 城镇历险

少年来到了城镇，街道上人来人往，热闹非凡。

他找了一家客栈住下，准备明天再去打听消息。

第三章 意外收获

在客栈里，少年遇到了一位老者。

老者说他骨骼清奇，是个练武的好材料。"""

    def test_split_by_chinese_titles(self):
        """应正确识别"第X章"格式的标题并切分。"""
        result = split_text_by_chapters(self.SAMPLE_TEXT)
        assert len(result.chapters) == 3
        assert result.chapters[0].title == "初入江湖"
        assert result.chapters[1].title == "城镇历险"
        assert result.chapters[2].title == "意外收获"

    def test_chapter_numbers(self):
        """章节编号应正确递增。"""
        result = split_text_by_chapters(self.SAMPLE_TEXT)
        numbers = [ch.number for ch in result.chapters]
        assert numbers == [1, 2, 3]

    def test_chapter_content(self):
        """每章内容应包含正文文本。"""
        result = split_text_by_chapters(self.SAMPLE_TEXT)
        assert "少年站在山巅" in result.chapters[0].raw_text
        assert "街道上人来人往" in result.chapters[1].raw_text
        assert "遇到了一位老者" in result.chapters[2].raw_text

    def test_split_english_chapter_titles(self):
        """应正确识别英文 Chapter N 格式。"""
        text = """Chapter 1: The Beginning

It was a dark and stormy night.

Chapter 2: The Journey

They set out at dawn."""
        result = split_text_by_chapters(text)
        assert len(result.chapters) == 2

    def test_split_no_chapters(self):
        """无法识别章节标题时应作为单章返回。"""
        text = "这是一段没有章节标题的普通文本，内容比较短。"
        result = split_text_by_chapters(text)
        assert len(result.chapters) == 1
        assert result.split_method == "single_chapter"


# ──────────────────────────────────────
# 章节编号提取
# ──────────────────────────────────────


class TestChapterNumberExtraction:
    """章节编号提取测试。"""

    def test_extract_arabic_number(self):
        assert extract_chapter_number("第12章 标题") == 12

    def test_extract_chinese_number(self):
        assert extract_chapter_number("第三章 标题") == 3

    def test_extract_english_number(self):
        assert extract_chapter_number("Chapter 5: Title") == 5

    def test_extract_complex_chinese(self):
        assert extract_chapter_number("第二十三回") == 23

    def test_no_number(self):
        assert extract_chapter_number("这是一个普通标题") is None


# ──────────────────────────────────────
# 文本解析工具
# ──────────────────────────────────────


class TestChapterParser:
    """基础文本解析测试。"""

    def test_split_paragraphs(self):
        text = "第一段内容\n\n第二段内容\n\n第三段内容"
        paragraphs = split_paragraphs(text)
        assert len(paragraphs) == 3

    def test_clean_text(self):
        text = "第一行\r\n第二行\r\n\n\n\n\n第三行"
        cleaned = clean_text(text)
        assert "\r" not in cleaned
        assert cleaned.count("\n\n") <= 1

    def test_extract_dialogue(self):
        text = '张三说："你好啊！"李四道："再见。"'
        dialogues = extract_dialogue(text)
        assert len(dialogues) >= 1
        # 第一句对话
        assert dialogues[0][1] == "你好啊！"


# ──────────────────────────────────────
# 顶层入口
# ──────────────────────────────────────


class TestNovelParser:
    """小说解析入口测试。"""

    def test_parse_text_content(self):
        """直接解析文本内容。"""
        text = """第一章 开始

少年踏上了旅程。

第二章 发展

他在路上遇到了很多人。"""
        info = parse_text_content(text, title="测试小说")
        assert info.name == "测试小说"
        assert info.chapter_count == 2
        assert info.total_chars > 0

    def test_parse_novel_directory(self, tmp_path):
        """解析目录模式的小说。"""
        novel_dir = tmp_path / "测试小说"
        origin = novel_dir / "origin"
        origin.mkdir(parents=True)

        # 创建两个章节文件
        (origin / "001.txt").write_text("第一章 标题一\n\n这是第一章的内容。", encoding="utf-8")
        (origin / "002.txt").write_text("第二章 标题二\n\n这是第二章的内容。", encoding="utf-8")

        from app.parsers import parse_novel
        info = parse_novel(novel_dir)
        assert info.chapter_count == 2
        assert info.parse_mode == "directory"

    def test_parse_novel_with_metadata(self, tmp_path):
        """解析带元数据文件的小说目录。"""
        novel_dir = tmp_path / "测试小说"
        origin = novel_dir / "origin"
        origin.mkdir(parents=True)

        (origin / "001.txt").write_text("第一章\n\n内容", encoding="utf-8")
        (novel_dir / "character.md").write_text("角色A: 主角\n角色B: 反派", encoding="utf-8")
        (novel_dir / "overview.md").write_text("一个关于冒险的故事", encoding="utf-8")

        from app.parsers import parse_novel
        info = parse_novel(novel_dir)
        assert info.has_character_file is True
        assert info.has_overview_file is True
        assert "角色A" in info.character_content
