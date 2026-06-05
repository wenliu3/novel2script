"""章节数据模型。

定义小说章节的数据结构，作为输入端的标准格式。
"""

from pydantic import BaseModel, Field


class ChapterMeta(BaseModel):
    """章节元信息（解析过程中提取）。"""

    has_dialogue: bool = Field(False, description="是否包含对话")
    paragraph_count: int = Field(0, description="段落数")
    character_names_seen: list[str] = Field(default_factory=list, description="本章出现的角色名")
    location_hints: list[str] = Field(default_factory=list, description="地点线索")


class Chapter(BaseModel):
    """章节信息。"""

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
