"""最终脚本数据模型。

聚合所有子模型，定义完整的 LRM 脚本结构。
这是 YAML 导出的顶层数据结构。
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.schema.scene import Scene


class ScriptMetadata(BaseModel):
    """脚本元信息。"""

    source_novel: str = Field("", description="来源小说名")
    total_chapters: int = Field(0, description="总章节数")
    total_scenes: int = Field(0, description="总场景数")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="生成时间 (ISO 8601)",
    )


class ChapterScript(BaseModel):
    """单章脚本。"""

    number: int = Field(..., description="章节编号")
    title: str = Field("", description="章节标题（英文）")
    scenes: list[Scene] = Field(default_factory=list, description="场景列表")


class Script(BaseModel):
    """完整 LRM 脚本（YAML 输出的顶层结构）。"""

    title: str = Field("", description="脚本标题")
    metadata: ScriptMetadata = Field(default_factory=ScriptMetadata)
    chapters: list[ChapterScript] = Field(default_factory=list)

    def total_scenes(self) -> int:
        """计算总场景数。"""
        return sum(len(ch.scenes) for ch in self.chapters)

    def total_shots(self) -> int:
        """计算总镜头数。"""
        return sum(
            len(s.shots)
            for ch in self.chapters
            for s in ch.scenes
        )
