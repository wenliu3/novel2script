"""PR-03 章节分析 Agent 测试。

覆盖：
- Schema 模型 (Chapter, ChapterAnalysis, KeyEvent, ChapterAnalysisReport)
- ChapterAgent 文件解析（扫描 + 标题提取 + 章节解析）
- ChapterAgent LLM 分析流程（Mock LLM）
- 边界条件和异常路径
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── 导入被测模块 ──

from app.schema.chapter import (
    Chapter,
    ChapterAnalysis,
    ChapterAnalysisReport,
    ChapterMeta,
    KeyEvent,
)
from app.agents.chapter_agent import ChapterAgent, MAX_CHAPTER_LENGTH
from app.services.llm_service import LLMService


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def mock_llm() -> MagicMock:
    """创建一个 Mock LLM 服务，返回预设的 JSON 响应。

    使用 side_effect 支持逐章返回不同的 chapter_number。
    """
    llm = MagicMock(spec=LLMService)

    def _response(system: str, user: str, **kwargs) -> dict:
        # 从 user message 中尝试找到章节编号（通过 text 内容匹配）
        # 默认用 1，因为单章测试用的是 chapter 1
        return _mock_llm_response(chapter_number=1)

    llm.prompt_json.side_effect = _response
    llm.prompt.return_value = json.dumps(_mock_llm_response(chapter_number=1))
    return llm


@pytest.fixture
def mock_llm_multi_chapter() -> MagicMock:
    """Mock LLM 服务，根据调用次数返回不同 chapter_number。"""
    llm = MagicMock(spec=LLMService)
    call_count = {"count": 0}

    def _response(system: str, user: str, **kwargs) -> dict:
        call_count["count"] += 1
        return _mock_llm_response(chapter_number=call_count["count"])

    llm.prompt_json.side_effect = _response
    return llm


@pytest.fixture
def chapter_agent(mock_llm: MagicMock) -> ChapterAgent:
    """使用 Mock LLM 创建 ChapterAgent 实例。"""
    return ChapterAgent(mock_llm)


@pytest.fixture
def sample_novel_dir() -> Path:
    """创建包含模拟章节文件的临时小说目录。

    目录结构：
        novel_name/origin/
            001_chapter1.txt
            002_chapter2.txt
            003_chapter3.txt
    """
    tmp = Path(tempfile.mkdtemp(prefix="novel_test_"))
    origin_dir = tmp / "origin"
    origin_dir.mkdir(parents=True)

    chapters = {
        1: "第一章 初入江湖\n\n张三背着行囊，走进了这座陌生的城市。街道两旁，商贩的叫卖声此起彼伏。\n\n他抬头看了看天色，已近黄昏。",
        2: "第二章 客栈风波\n\n客栈大堂里，几个壮汉正在喝酒划拳。张三找了个角落坐下。\n\n\"客官，打尖还是住店？\"小二热情地迎上来。\n\n\"住店。\"张三简短地回答。",
        3: "第三章 夜半惊魂\n\n半夜，张三被一阵奇怪的声音惊醒。他悄悄起身，推开房门。\n\n走廊尽头，一个黑影一闪而过。\n\n\"谁？\"他低声问道。",
    }

    for num, text in chapters.items():
        file_path = origin_dir / f"{num:03d}_chapter{num}.txt"
        file_path.write_text(text, encoding="utf-8")

    return tmp


@pytest.fixture
def sample_chapters(sample_novel_dir: Path) -> list[Chapter]:
    """用 ChapterAgent 解析测试目录得到的章节列表。"""
    agent = ChapterAgent(MagicMock(spec=LLMService))
    return agent.execute(sample_novel_dir)


# ═══════════════════════════════════════════════════════════════
# 1. Schema 模型测试
# ═══════════════════════════════════════════════════════════════


class TestKeyEvent:
    """KeyEvent 模型测试。"""

    def test_create_minimal(self) -> None:
        evt = KeyEvent(
            event_id="evt_1_01",
            description="张三进入客栈",
            participants=["张三"],
            location="客栈大堂",
        )
        assert evt.event_id == "evt_1_01"
        assert evt.importance == "major"  # 默认值
        assert evt.start_hint == ""  # 默认值

    def test_create_full(self) -> None:
        evt = KeyEvent(
            event_id="evt_1_02",
            description="深夜发现黑影",
            participants=["张三", "神秘人"],
            location="客栈走廊",
            importance="major",
            start_hint="半夜，张三被一阵奇怪的声音惊醒",
        )
        assert evt.importance == "major"
        assert len(evt.participants) == 2
        assert "张三" in evt.participants

    def test_serialize_to_dict(self) -> None:
        evt = KeyEvent(
            event_id="evt_1_01",
            description="测试事件",
            participants=["角色A"],
            location="地点A",
            importance="minor",
        )
        d = evt.model_dump()
        assert d["event_id"] == "evt_1_01"
        assert d["description"] == "测试事件"
        assert d["importance"] == "minor"


class TestChapterAnalysis:
    """ChapterAnalysis 模型测试。"""

    def test_create_with_events(self) -> None:
        events = [
            KeyEvent(
                event_id="evt_1_01",
                description="事件1",
                participants=["A"],
                location="L1",
                importance="major",
            ),
            KeyEvent(
                event_id="evt_1_02",
                description="事件2",
                participants=["B"],
                location="L2",
                importance="minor",
            ),
            KeyEvent(
                event_id="evt_1_03",
                description="事件3",
                participants=["C"],
                location="L3",
                importance="setup",
            ),
        ]
        analysis = ChapterAnalysis(
            chapter_number=1,
            chapter_title="第一章",
            summary="本章讲述了张三初入江湖的故事...",
            key_events=events,
            characters_seen=["张三", "李四 [新]", "王五"],
            location_hints=["客栈", "街道", "密室"],
            emotion_tone="悬疑",
            word_count=3500,
        )
        assert analysis.event_count == 3
        assert analysis.chapter_number == 1

    def test_major_events_property(self) -> None:
        events = [
            KeyEvent(
                event_id="evt_1_01",
                description="主线事件",
                participants=["A"],
                importance="major",
            ),
            KeyEvent(
                event_id="evt_1_02",
                description="支线事件",
                participants=["B"],
                importance="minor",
            ),
            KeyEvent(
                event_id="evt_1_03",
                description="伏笔",
                participants=["C"],
                importance="setup",
            ),
        ]
        analysis = ChapterAnalysis(
            chapter_number=1,
            chapter_title="",
            summary="",
            key_events=events,
        )
        major = analysis.major_events
        assert len(major) == 1
        assert major[0].event_id == "evt_1_01"

    def test_empty_analysis(self) -> None:
        """空章节分析（用于 LLM 失败回退）。"""
        analysis = ChapterAnalysis(chapter_number=5, chapter_title="")
        assert analysis.event_count == 0
        assert analysis.major_events == []
        assert analysis.characters_seen == []
        assert analysis.word_count == 0

    def test_serialize_to_dict(self) -> None:
        analysis = ChapterAnalysis(
            chapter_number=2,
            chapter_title="第二章",
            summary="摘要内容",
            key_events=[
                KeyEvent(
                    event_id="evt_2_01",
                    description="事件",
                    participants=["A"],
                    importance="major",
                )
            ],
            characters_seen=["A"],
            location_hints=["L1"],
            emotion_tone="紧张",
        )
        d = analysis.model_dump()
        assert d["chapter_number"] == 2
        assert len(d["key_events"]) == 1
        assert d["emotion_tone"] == "紧张"


class TestChapterAnalysisReport:
    """ChapterAnalysisReport 汇总报告测试。"""

    def _make_analyses(self) -> list[ChapterAnalysis]:
        return [
            ChapterAnalysis(
                chapter_number=1,
                chapter_title="第一章",
                summary="第一章摘要...",
                key_events=[
                    KeyEvent(
                        event_id="evt_1_01",
                        description="事件A",
                        participants=["张三"],
                        importance="major",
                    )
                ],
                characters_seen=["张三", "李四"],
                location_hints=["客栈"],
                emotion_tone="悬疑",
            ),
            ChapterAnalysis(
                chapter_number=2,
                chapter_title="第二章",
                summary="第二章摘要...",
                key_events=[
                    KeyEvent(
                        event_id="evt_2_01",
                        description="事件B",
                        participants=["张三", "王五"],
                        importance="major",
                    ),
                    KeyEvent(
                        event_id="evt_2_02",
                        description="事件C",
                        participants=["李四"],
                        importance="minor",
                    ),
                ],
                characters_seen=["张三", "王五"],
                location_hints=["街道", "密室"],
                emotion_tone="紧张",
            ),
        ]

    def test_summaries_format(self) -> None:
        """验证 summaries 属性输出 plan.md 要求的格式。"""
        report = ChapterAnalysisReport(
            analyses=self._make_analyses(),
            total_chapters=2,
            total_events=3,
            all_characters=["张三", "李四", "王五"],
            all_locations=["客栈", "街道", "密室"],
        )

        summaries = report.summaries
        assert summaries == [
            {"chapter": 1, "summary": "第一章摘要..."},
            {"chapter": 2, "summary": "第二章摘要..."},
        ]

    def test_aggregation_fields(self) -> None:
        report = ChapterAnalysisReport(
            analyses=self._make_analyses(),
            total_chapters=2,
            total_events=3,
            all_characters=["张三", "李四", "王五"],
            all_locations=["客栈", "街道", "密室"],
        )
        assert report.total_chapters == 2
        assert report.total_events == 3
        assert len(report.all_characters) == 3
        assert len(report.all_locations) == 3

    def test_empty_report(self) -> None:
        report = ChapterAnalysisReport()
        assert report.total_chapters == 0
        assert report.total_events == 0
        assert report.summaries == []


class TestChapterModel:
    """Chapter（文件解析）模型测试。"""

    def test_word_count(self) -> None:
        ch = Chapter(number=1, title="测试", raw_text="四个汉字测试")
        assert ch.word_count == 6

    def test_char_count(self) -> None:
        ch = Chapter(number=1, original_text="hello世界")
        assert ch.char_count == 7

    def test_default_meta(self) -> None:
        ch = Chapter(number=1)
        assert ch.meta.has_dialogue is False
        assert ch.meta.paragraph_count == 0


# ═══════════════════════════════════════════════════════════════
# 2. ChapterAgent 文件解析测试
# ═══════════════════════════════════════════════════════════════


class TestChapterAgentParsing:
    """ChapterAgent 文件解析阶段测试（不使用 LLM）。"""

    def test_scan_chapters(self, sample_novel_dir: Path, chapter_agent: ChapterAgent) -> None:
        """测试扫描 origin/ 目录获取章节文件列表。"""
        chapter_files = chapter_agent._scan_chapters(sample_novel_dir / "origin")
        assert len(chapter_files) == 3
        assert chapter_files[1].name == "001_chapter1.txt"
        assert chapter_files[2].name == "002_chapter2.txt"
        assert chapter_files[3].name == "003_chapter3.txt"

    def test_execute_returns_chapters(
        self, sample_novel_dir: Path, chapter_agent: ChapterAgent
    ) -> None:
        """测试 execute() 方法返回正确的 Chapter 列表。"""
        chapters = chapter_agent.execute(sample_novel_dir)
        assert len(chapters) == 3

        # 章节编号正确
        assert chapters[0].number == 1
        assert chapters[1].number == 2
        assert chapters[2].number == 3

        # 标题提取正确
        assert chapters[0].title in ("初入江湖", "第一章 初入江湖")
        assert chapters[1].title in ("客栈风波", "第二章 客栈风波")

        # 内容不为空
        for ch in chapters:
            assert len(ch.raw_text) > 0
            assert ch.word_count > 0

    def test_execute_missing_origin_dir(
        self, chapter_agent: ChapterAgent, tmp_path: Path
    ) -> None:
        """测试 origin/ 目录不存在时抛出异常。"""
        with pytest.raises(FileNotFoundError, match="章节目录不存在"):
            chapter_agent.execute(tmp_path)

    def test_extract_title_chinese(self, chapter_agent: ChapterAgent) -> None:
        """测试中文章节标题提取。"""
        text = "第三章 夜探王府\n\n正文内容..."
        title = chapter_agent._extract_title(text)
        assert title in ("夜探王府", "第三章 夜探王府")

    def test_extract_title_english(self, chapter_agent: ChapterAgent) -> None:
        """测试英文章节标题提取。"""
        text = "Chapter 5: The Dark Forest\n\n正文内容..."
        title = chapter_agent._extract_title(text)
        assert title in ("The Dark Forest", "Chapter 5: The Dark Forest")

    def test_extract_title_short_line(self, chapter_agent: ChapterAgent) -> None:
        """测试短行作为标题提取。"""
        text = "诡夜客栈\n\n正文内容很长很长..."
        title = chapter_agent._extract_title(text)
        assert title == "诡夜客栈"

    def test_extract_title_empty(self, chapter_agent: ChapterAgent) -> None:
        """测试空文本标题提取。"""
        assert chapter_agent._extract_title("") == ""

    def test_chapter_encoding_detection(
        self, chapter_agent: ChapterAgent, sample_novel_dir: Path
    ) -> None:
        """测试章节文件编码正确记录。"""
        chapters = chapter_agent.execute(sample_novel_dir)
        for ch in chapters:
            assert ch.encoding in ("utf-8", "gbk", "gb2312", "gb18030")

    def test_file_path_recorded(
        self, chapter_agent: ChapterAgent, sample_novel_dir: Path
    ) -> None:
        """测试文件路径被正确记录。"""
        chapters = chapter_agent.execute(sample_novel_dir)
        for ch in chapters:
            assert len(ch.file_path) > 0
            assert "chapter" in ch.file_path.lower()


# ═══════════════════════════════════════════════════════════════
# 3. ChapterAgent LLM 分析测试（Mock）
# ═══════════════════════════════════════════════════════════════


class TestChapterAgentAnalysis:
    """ChapterAgent LLM 分析阶段测试（使用 Mock LLM）。"""

    def test_analyze_chapter_success(
        self,
        chapter_agent: ChapterAgent,
        mock_llm: MagicMock,
    ) -> None:
        """测试单章 LLM 分析成功路径。"""
        chapter = Chapter(
            number=1,
            title="初入江湖",
            raw_text="张三背着行囊走进了陌生的城市...",
        )
        analysis = chapter_agent.analyze_chapter(chapter)

        assert analysis.chapter_number == 1
        # Mock 返回的标题是 "第1章：初入江湖"
        assert "初入江湖" in analysis.chapter_title
        assert len(analysis.summary) > 0
        assert analysis.event_count == 3
        assert len(analysis.characters_seen) > 0
        assert len(analysis.location_hints) > 0
        assert analysis.emotion_tone != ""
        # LLM 应该被调用了一次
        mock_llm.prompt_json.assert_called_once()

    def test_analyze_chapter_empty_text(
        self,
        chapter_agent: ChapterAgent,
        mock_llm: MagicMock,
    ) -> None:
        """测试空文本章节不调用 LLM 直接返回空分析。"""
        chapter = Chapter(number=5, title="空章节", raw_text="")
        analysis = chapter_agent.analyze_chapter(chapter)

        assert analysis.chapter_number == 5
        assert analysis.word_count == 0
        assert analysis.event_count == 0
        # 空文本不调用 LLM
        mock_llm.prompt_json.assert_not_called()

    def test_analyze_chapter_llm_error(
        self,
        mock_llm: MagicMock,
    ) -> None:
        """测试 LLM 调用失败时的优雅降级。"""
        mock_llm.prompt_json.side_effect = RuntimeError("API 超时")

        agent = ChapterAgent(mock_llm)
        chapter = Chapter(
            number=1,
            title="测试",
            raw_text="一些测试文本...",
        )
        analysis = agent.analyze_chapter(chapter)

        # 不抛异常，返回空分析
        assert analysis.chapter_number == 1
        assert analysis.event_count == 0
        assert analysis.word_count == len(chapter.raw_text)

    def test_analyze_chapter_long_text_truncation(
        self,
        mock_llm: MagicMock,
    ) -> None:
        """测试超长文本被截断后再传给 LLM。"""
        agent = ChapterAgent(mock_llm)

        # 生成远超过 MAX_CHAPTER_LENGTH 的文本
        long_text = "正文内容。" * (MAX_CHAPTER_LENGTH // 5 + 100)
        chapter = Chapter(number=1, title="长章节", raw_text=long_text)
        agent.analyze_chapter(chapter)

        # 验证传给 LLM 的 user content 长度不超过 MAX_CHAPTER_LENGTH
        call_args = mock_llm.prompt_json.call_args
        assert call_args is not None
        # prompt_json(system, user) — user 是第二个位置参数
        user_content: str = call_args[0][1]
        # user_content 是渲染后的 prompt，包含模板文本 + 截断的章节文本
        # 所以它应该 >= 截断后章节文本长度，但应 <= MAX_CHAPTER_LENGTH + 模板长度
        # 核心断言：原始超长文本没有完整传入
        assert long_text not in user_content, "超长原文不应完整传入 LLM"

    def test_analyze_chapters_batch(
        self,
        mock_llm_multi_chapter: MagicMock,
        sample_chapters: list[Chapter],
    ) -> None:
        """测试批量章节分析。"""
        agent = ChapterAgent(mock_llm_multi_chapter)

        report = agent.analyze_chapters(sample_chapters)

        assert report.total_chapters == 3
        assert len(report.analyses) == 3
        assert report.total_events > 0
        assert len(report.all_characters) > 0
        assert len(report.all_locations) > 0
        # LLM 被调用了 3 次（每章一次）
        assert mock_llm_multi_chapter.prompt_json.call_count == 3
        # 验证各章 chapter_number 正确
        for i, a in enumerate(report.analyses, 1):
            assert a.chapter_number == i

    def test_analyze_chapters_empty_list(
        self,
        chapter_agent: ChapterAgent,
    ) -> None:
        """测试空章节列表的分析。"""
        report = chapter_agent.analyze_chapters([])
        assert report.total_chapters == 0
        assert report.analyses == []

    def test_summaries_output_format(
        self,
        chapter_agent: ChapterAgent,
        sample_chapters: list[Chapter],
    ) -> None:
        """测试 summaries 输出符合 plan.md 规范。"""
        report = chapter_agent.analyze_chapters(sample_chapters)

        summaries = report.summaries
        assert len(summaries) == 3
        for s in summaries:
            assert "chapter" in s
            assert "summary" in s
            assert isinstance(s["chapter"], int)
            assert isinstance(s["summary"], str)

    def test_run_full_pipeline(
        self,
        mock_llm_multi_chapter: MagicMock,
        sample_novel_dir: Path,
    ) -> None:
        """测试 run_full_pipeline() 完整流程。"""
        agent = ChapterAgent(mock_llm_multi_chapter)
        chapters, report = agent.run_full_pipeline(sample_novel_dir)

        assert len(chapters) == 3
        assert report.total_chapters == 3
        assert len(report.analyses) == 3
        # 验证章节与分析一一对应
        for ch, analysis in zip(chapters, report.analyses):
            assert ch.number == analysis.chapter_number


# ═══════════════════════════════════════════════════════════════
# 4. 集成测试：解析 → 分析数据流
# ═══════════════════════════════════════════════════════════════


class TestParsingToAnalysisPipeline:
    """测试从文件解析到 LLM 分析的完整数据流。"""

    def test_chapter_to_analysis_mapping(
        self,
        mock_llm_multi_chapter: MagicMock,
        sample_chapters: list[Chapter],
    ) -> None:
        """测试解析出的 Chapter 能正确传递给 analyze_chapter。"""
        agent = ChapterAgent(mock_llm_multi_chapter)
        report = agent.analyze_chapters(sample_chapters)

        # 每个 Chapter 对应一个 ChapterAnalysis
        assert len(sample_chapters) == len(report.analyses)

        for chapter, analysis in zip(sample_chapters, report.analyses):
            assert chapter.number == analysis.chapter_number
            assert analysis.word_count == chapter.word_count


class TestCharacterListAggregation:
    """测试角色和地点汇总去重。"""

    def test_character_dedup(self) -> None:
        """测试跨章角色去重。"""
        analyses = [
            ChapterAnalysis(
                chapter_number=1,
                chapter_title="",
                summary="",
                characters_seen=["张三", "李四"],
                location_hints=["客栈"],
            ),
            ChapterAnalysis(
                chapter_number=2,
                chapter_title="",
                summary="",
                characters_seen=["张三", "王五"],
                location_hints=["客栈", "街道"],
            ),
        ]
        report = ChapterAnalysisReport(
            analyses=analyses,
            total_chapters=2,
            total_events=0,
            all_characters=sorted({"张三", "李四", "王五"}),
            all_locations=sorted({"客栈", "街道"}),
        )
        assert len(report.all_characters) == 3
        assert "张三" in report.all_characters
        assert len(report.all_locations) == 2


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _mock_llm_response(chapter_number: int = 1) -> dict:
    """构造模拟的 LLM JSON 响应。"""
    return {
        "chapter_number": chapter_number,
        "chapter_title": f"第{chapter_number}章：初入江湖" if chapter_number == 1 else f"第{chapter_number}章",
        "summary": f"本章讲述了主角在第{chapter_number}章的冒险经历。他遇到了新的挑战和盟友，故事由此展开。",
        "key_events": [
            {
                "event_id": f"evt_{chapter_number}_01",
                "description": "主角到达新地点并遭遇困境",
                "participants": ["张三", "李四"],
                "location": "客栈大堂",
                "importance": "major",
                "start_hint": "张三推开门",
            },
            {
                "event_id": f"evt_{chapter_number}_02",
                "description": "与配角发生冲突",
                "participants": ["张三"],
                "location": "街道",
                "importance": "minor",
                "start_hint": "忽然身后传来",
            },
            {
                "event_id": f"evt_{chapter_number}_03",
                "description": "发现关键线索的伏笔",
                "participants": ["张三"],
                "location": "密室",
                "importance": "setup",
                "start_hint": "角落里有一封",
            },
        ],
        "characters_seen": ["张三", "李四", "王五 [新]"],
        "location_hints": ["客栈", "街道", "密室"],
        "emotion_tone": "悬疑",
    }
