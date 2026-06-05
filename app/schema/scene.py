"""场景数据模型。

定义 LRM 脚本中场景的数据结构，包括场景元信息、镜头列表等。
"""

from pydantic import BaseModel, Field


class Shot(BaseModel):
    """单个镜头。"""

    id: str = Field(..., description="镜头唯一 ID，如 ch1_s1_sh1")
    camera_angle: str = Field("", description="机位角度：low_angle, high_angle, eye_level, bird_eye 等")
    shot_type: str = Field("", description="景别：extreme_close_up, close_up, medium_shot, wide_shot 等")
    frame_description: str = Field("", description="画面内容详细描述")
    movement: str = Field("static", description="镜头运动：static, pan, tilt, dolly, tracking 等")
    duration_seconds: float = Field(5.0, description="预计持续时间（秒）")
    dialogue: list["DialogueLine"] = Field(default_factory=list, description="对话列表")
    narration: str = Field("", description="旁白/叙述（英文）")
    visual_effects: str = Field("", description="视觉特效说明")


class DialogueLine(BaseModel):
    """对话行。"""

    character: str = Field(..., description="角色名（英文）")
    line: str = Field(..., description="台词（英文）")
    emotion: str = Field("", description="情感状态")


# 解决前向引用
Shot.model_rebuild()


class Scene(BaseModel):
    """场景。"""

    id: str = Field(..., description="场景唯一 ID，如 ch1_s1")
    title: str = Field("", description="场景标题")
    location: str = Field("", description="场景地点")
    time: str = Field("", description="时间：dawn, morning, afternoon, dusk, night 等")
    mood: str = Field("", description="氛围/情绪：tense, peaceful, mysterious 等")
    props: list[str] = Field(default_factory=list, description="关键道具列表")
    shots: list[Shot] = Field(default_factory=list, description="镜头列表")
