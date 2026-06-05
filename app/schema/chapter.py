"""章节数据模型。

定义小说章节的数据结构，包括输入端的标准格式和 LLM 分析结果。
"""

from pydantic import BaseModel, Field


class ChapterMeta(BaseModel):
    """章节元信息（解析过程中提取）。"""

    has_dialogue: bool = Field(False, description="是否包含对话")
    paragraph_count: int = Field(0, description="段落数")
    character_names_seen: list[str] = Field(default_factory=list, description="本章出现的角色名")
    location_hints: list[str] = Field(default_factory=list, description="地点线索")


class Chapter(BaseModel):
    """章节信息（文件解析输出）。"""

    number: int = Field(..., description="章节编号")
    title: str = Field("", description="章节标题（中文）")
    raw_text: str = Field("", description="章节原文（清理后）")
    original_text: str = Field("", description="章节原文（清理前，保留原始格式）")
    file_path: str = Field("", description="源文件路径")
    encoding: str = Field("utf-8", description="检测到的文件编码")
    meta: ChapterMeta = Field(default_factory=ChapterMeta)

    @property
    def word_count(self) -> int:
        """返回章节字数。"""
        return len(self.raw_text)

    @property
    def char_count(self) -> int:
        """返回章节字符数（含标点）。"""
        return len(self.original_text)


# ── PR-03: 章节分析相关模型 ──


class KeyEvent(BaseModel):
    """关键事件。

    由 Chapter Analyzer Agent 从章节文本中提取。
    """

    event_id: str = Field("", description="事件唯一 ID，如 evt_001")
    description: str = Field("", description="事件描述（中文，50-200字）")
    participants: list[str] = Field(default_factory=list, description="参与该事件的角色名列表")
    location: str = Field("", description="事件发生的地点")
    importance: str = Field("major", description="事件重要性：major（推动主线）| minor（支线/铺垫）| setup（伏笔/铺垫）")
    start_hint: str = Field("", description="事件在原文中的起始线索（前20字）")


class ChapterAnalysis(BaseModel):
    """章节分析结果（LLM 分析输出）。

    由 Chapter Analyzer Agent 调用 LLM 生成，包含：
    - 章节摘要
    - 关键事件列表
    - 出场角色
    - 地点线索
    - 情感基调

    这是 PR-03 的核心输出。
    """

    chapter_number: int = Field(..., description="章节编号")
    chapter_title: str = Field("", description="章节标题")
    summary: str = Field("", description="章节摘要（中文，200-500字）")
    key_events: list[KeyEvent] = Field(default_factory=list, description="关键事件列表（3-8个）")
    characters_seen: list[str] = Field(default_factory=list, description="本章出现的角色名列表")
    location_hints: list[str] = Field(default_factory=list, description="地点/场景线索列表")
    emotion_tone: str = Field("", description="本章情感基调，如：紧张、温馨、悲伤、悬疑")
    word_count: int = Field(0, description="章节字数")

    @property
    def major_events(self) -> list[KeyEvent]:
        """获取推动主线的重要事件。"""
        return [e for e in self.key_events if e.importance == "major"]

    @property
    def event_count(self) -> int:
        """关键事件数量。"""
        return len(self.key_events)


class ChapterAnalysisReport(BaseModel):
    """多章分析汇总报告。

    包含所有章节的分析结果和分析元信息。
    """

    analyses: list[ChapterAnalysis] = Field(default_factory=list, description="各章分析结果")
    total_chapters: int = Field(0, description="总分析章节数")
    total_events: int = Field(0, description="总关键事件数")
    all_characters: list[str] = Field(default_factory=list, description="所有章节中出现的角色（去重）")
    all_locations: list[str] = Field(default_factory=list, description="所有章节中出现的地点（去重）")

    @property
    def summaries(self) -> list[dict]:
        """以 plan.md 中指定的简洁格式返回各章摘要。"""
        return [
            {"chapter": a.chapter_number, "summary": a.summary}
            for a in self.analyses
        ]
