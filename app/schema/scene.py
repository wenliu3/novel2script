"""场景数据模型。

定义 LRM 脚本中场景的数据结构，包括场景元信息、镜头列表等。
支持场景规划、连续性追踪、转场设计等功能。
"""

from enum import Enum

from pydantic import BaseModel, Field


class ShotType(str, Enum):
    """景别类型。"""

    EXTREME_CLOSE_UP = "extreme_close_up"    # 大特写
    CLOSE_UP = "close_up"                     # 特写
    MEDIUM_CLOSE_UP = "medium_close_up"       # 近景
    MEDIUM_SHOT = "medium_shot"               # 中景
    MEDIUM_FULL_SHOT = "medium_full_shot"     # 中全景
    FULL_SHOT = "full_shot"                   # 全景
    WIDE_SHOT = "wide_shot"                   # 远景
    EXTREME_WIDE_SHOT = "extreme_wide_shot"   # 大远景


class CameraAngle(str, Enum):
    """机位角度。"""

    EYE_LEVEL = "eye_level"         # 平视
    LOW_ANGLE = "low_angle"         # 仰拍
    HIGH_ANGLE = "high_angle"       # 俯拍
    BIRD_EYE = "bird_eye"          # 鸟瞰
    DUTCH_ANGLE = "dutch_angle"     # 倾斜
    WORMS_EYE = "worms_eye"        # 蚁视


class CameraMovement(str, Enum):
    """镜头运动。"""

    STATIC = "static"               # 固定
    PAN_LEFT = "pan_left"           # 左摇
    PAN_RIGHT = "pan_right"         # 右摇
    TILT_UP = "tilt_up"             # 上摇
    TILT_DOWN = "tilt_down"         # 下摇
    DOLLY_IN = "dolly_in"           # 推
    DOLLY_OUT = "dolly_out"         # 拉
    TRACKING = "tracking"           # 跟拍
    CRANE_UP = "crane_up"           # 升
    CRANE_DOWN = "crane_down"       # 降
    ZOOM_IN = "zoom_in"             # 变焦推
    ZOOM_OUT = "zoom_out"           # 变焦拉


class TransitionType(str, Enum):
    """场景转场类型。"""

    CUT = "cut"                     # 直切
    FADE_IN = "fade_in"             # 淡入
    FADE_OUT = "fade_out"           # 淡出
    DISSOLVE = "dissolve"           # 叠化
    WIPE = "wipe"                   # 划变
    MATCH_CUT = "match_cut"         # 匹配剪辑
    JUMP_CUT = "jump_cut"           # 跳切
    CROSS_DISSOLVE = "cross_dissolve"  # 交叉叠化


class SceneTag(str, Enum):
    """场景标签（分类标记）。"""

    ACTION = "action"               # 动作戏
    DIALOGUE = "dialogue"           # 对话戏
    NARRATION = "narration"         # 旁白/叙述
    FLASHBACK = "flashback"         # 回忆/闪回
    MONTAGE = "montage"             # 蒙太奇
    ESTABLISHING = "establishing"   # 建立镜头
    TRANSITION = "transition"       # 过渡场景
    CLIMAX = "climax"               # 高潮
    QUIET = "quiet"                 # 静谧/抒情


class Shot(BaseModel):
    """单个镜头。"""

    id: str = Field(..., description="镜头唯一 ID，如 ch1_s1_sh1")
    camera_angle: str = Field("", description="机位角度")
    shot_type: str = Field("", description="景别")
    frame_description: str = Field("", description="画面内容详细描述（英文）")
    movement: str = Field("static", description="镜头运动")
    duration_seconds: float = Field(5.0, description="预计持续时间（秒）")
    dialogue: list["DialogueLine"] = Field(default_factory=list, description="对话列表")
    narration: str = Field("", description="旁白/叙述（英文）")
    visual_effects: str = Field("", description="视觉特效说明")
    sound_effects: str = Field("", description="音效说明")
    lighting: str = Field("", description="灯光说明")


class DialogueLine(BaseModel):
    """对话行。"""

    character: str = Field(..., description="角色名（英文）")
    line: str = Field(..., description="台词（英文）")
    emotion: str = Field("", description="情感状态")
    action: str = Field("", description="伴随动作描述")


# ── PR-05: 节拍模型（叙述 → 对白 + 动作的最小叙事单元） ──


class Beat(BaseModel):
    """剧本节拍：动作或对白的最小叙事单元。

    由 DialogueAgent 从小说叙述中提取。
    是连接小说叙事和影视脚本的中间层。
    """

    type: str = Field(..., description="节拍类型：action（动作）| dialogue（对白）| narration（旁白）")
    character: str = Field("", description="角色名（对白为说话者，动作为执行者）")
    content: str = Field(..., description="内容描述（中文）")


# 解决前向引用
Shot.model_rebuild()


class Scene(BaseModel):
    """场景。"""

    id: str = Field(..., description="场景唯一 ID，如 ch1_s1")
    title: str = Field("", description="场景标题（英文）")
    location: str = Field("", description="场景地点（英文）")
    time: str = Field("", description="时间：dawn, morning, afternoon, dusk, night 等")
    mood: str = Field("", description="氛围/情绪：tense, peaceful, mysterious 等")
    summary: str = Field("", description="场景摘要（一句话描述本场景的核心事件）")
    tags: list[str] = Field(default_factory=list, description="场景标签：action, dialogue, flashback 等")
    transition_in: str = Field("cut", description="进入本场景的转场方式")
    transition_out: str = Field("cut", description="离开本场景的转场方式")
    estimated_duration: float = Field(0.0, description="预计场景总时长（秒），0 表示由镜头累加")
    props: list[str] = Field(default_factory=list, description="关键道具列表")
    characters_present: list[str] = Field(default_factory=list, description="本场景出场角色（英文名）")
    continuity_notes: str = Field("", description="连续性备注（角色状态、位置等）")
    beats: list[Beat] = Field(default_factory=list, description="节拍列表（由 DialogueAgent 生成）")
    shots: list[Shot] = Field(default_factory=list, description="镜头列表")

    @property
    def action_beats(self) -> list[Beat]:
        """获取所有动作节拍。"""
        return [b for b in self.beats if b.type == "action"]

    @property
    def dialogue_beats(self) -> list[Beat]:
        """获取所有对白节拍。"""
        return [b for b in self.beats if b.type == "dialogue"]

    @property
    def total_duration(self) -> float:
        """计算场景总时长（优先用 estimated_duration，否则累加镜头时长）。"""
        if self.estimated_duration > 0:
            return self.estimated_duration
        return sum(s.duration_seconds for s in self.shots) if self.shots else 0.0

    @property
    def shot_count(self) -> int:
        return len(self.shots)

    @property
    def dialogue_count(self) -> int:
        return sum(len(s.dialogue) for s in self.shots)

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags


class ScenePlan(BaseModel):
    """整章的场景规划结果。"""

    chapter_number: int = Field(..., description="章节编号")
    chapter_title: str = Field("", description="章节标题")
    scenes: list[Scene] = Field(default_factory=list, description="场景列表")
    total_estimated_duration: float = Field(0.0, description="整章预计总时长（秒）")
    scene_count: int = Field(0, description="场景数量")
    key_events: list[str] = Field(default_factory=list, description="本章关键事件摘要")

    def validate_structure(self) -> list[str]:
        """快速结构校验，返回错误列表。"""
        errors = []
        if not self.scenes:
            errors.append(f"第{self.chapter_number}章没有场景")
        for i, scene in enumerate(self.scenes):
            if not scene.title:
                errors.append(f"场景 {scene.id} 缺少标题")
            if not scene.location:
                errors.append(f"场景 {scene.id} 缺少地点")
            if i > 0 and scene.transition_in == "cut" and not scene.characters_present:
                # 非首个场景默认 cut 可能不合理
                pass  # 警告级别，不报错
        return errors
