"""最终脚本数据模型。

聚合所有子模型，定义完整的 LRM 脚本结构。
这是 YAML 导出的顶层数据结构。
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.schema.scene import Scene


class ScriptCharacter(BaseModel):
    """脚本角色（用于 YAML 输出的 characters 段）。"""

    id: str = Field(..., description="角色唯一 ID，如 char_001")
    name: str = Field(..., description="角色姓名（中文）")
    role: str = Field("配角", description="角色定位：主角/重要配角/配角/龙套")
    traits: list[str] = Field(default_factory=list, description="性格标签")
    motivation: str = Field("", description="角色动机")


class ScriptMetadata(BaseModel):
    """脚本元信息。"""

    source_novel: str = Field("", description="来源小说名")
    total_chapters: int = Field(0, description="总章节数")
    total_scenes: int = Field(0, description="总场景数")
    total_beats: int = Field(0, description="总节拍数")
    total_shots: int = Field(0, description="总镜头数")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="生成时间 (ISO 8601)",
    )


class ChapterScript(BaseModel):
    """单章脚本。"""

    number: int = Field(..., description="章节编号")
    title: str = Field("", description="章节标题")
    scenes: list[Scene] = Field(default_factory=list, description="场景列表")


class Script(BaseModel):
    """完整 LRM 脚本（YAML 输出的顶层结构）。"""

    title: str = Field("", description="脚本标题")
    genre: str = Field("", description="剧本类型：悬疑/武侠/言情/科幻 等")
    logline: str = Field("", description="一句话梗概")
    source: dict = Field(default_factory=dict, description="来源信息")
    characters: list[ScriptCharacter] = Field(default_factory=list, description="角色列表")
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

    def total_beats(self) -> int:
        """计算总节拍数。"""
        return sum(
            len(s.beats)
            for ch in self.chapters
            for s in ch.scenes
        )
