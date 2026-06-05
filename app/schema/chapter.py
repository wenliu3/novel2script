"""章节数据模型。

定义小说章节的数据结构，作为输入端的标准格式。
"""

from pydantic import BaseModel, Field


class Chapter(BaseModel):
    """章节信息。"""

    number: int = Field(..., description="章节编号")
    title: str = Field("", description="章节标题（中文）")
    raw_text: str = Field("", description="章节原文")
    file_path: str = Field("", description="源文件路径")

    @property
    def word_count(self) -> int:
        """返回章节字数。"""
        return len(self.raw_text)
