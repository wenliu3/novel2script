"""LRM 脚本 YAML Schema 定义。

定义最终输出 YAML 文件的完整数据结构，包括：
- 顶层元数据（版本、生成信息、统计）
- 章节/场景/镜头层级结构
- 角色定义
- 镜头语言规范（机位、景别、运动、灯光、音效）
- 场景转场定义
- 对话与旁白格式

YAML 输出示例见 app/schema/yaml_example.yaml
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 版本与配置
# ============================================================

YAML_SCHEMA_VERSION = "1.0"


class ScriptConfig(BaseModel):
    """生成配置。"""

    model_used: str = Field("", description="使用的 LLM 模型")
    language_source: str = Field("zh", description="源语言")
    language_target: str = Field("en", description="目标语言")
    temperature: float = Field(0.7, description="生成温度")
    max_tokens: int = Field(4096, description="最大 token 数")


# ============================================================
# 统计信息
# ============================================================


class ScriptStats(BaseModel):
    """脚本统计信息。"""

    total_chapters: int = Field(0, description="总章节数")
    total_scenes: int = Field(0, description="总场景数")
    total_shots: int = Field(0, description="总镜头数")
    total_dialogue_lines: int = Field(0, description="总对话行数")
    estimated_duration_minutes: float = Field(0.0, description="预估总时长（分钟）")
    estimated_word_count: int = Field(0, description="英文脚本预估字数")


# ============================================================
# 元数据
# ============================================================


class ScriptMetadata(BaseModel):
    """脚本元数据。"""

    schema_version: str = Field(YAML_SCHEMA_VERSION, description="Schema 版本")
    source_novel: str = Field("", description="来源小说名")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="生成时间 (ISO 8601)",
    )
    generator: str = Field("novel2script", description="生成器名称")
    generator_version: str = Field("0.1.0", description="生成器版本")
    stats: ScriptStats = Field(default_factory=ScriptStats)
    config: ScriptConfig = Field(default_factory=ScriptConfig)


# ============================================================
# 角色定义
# ============================================================


class ScriptCharacter(BaseModel):
    """YAML 输出中的角色定义。"""

    name: str = Field(..., description="角色中文名")
    english_name: str = Field("", description="英文名")
    aliases: list[str] = Field(default_factory=list, description="别名列表")
    role: str = Field("minor", description="角色定位: protagonist/antagonist/supporting/minor")
    importance: int = Field(0, description="重要度 0-10")
    gender: str = Field("", description="性别")
    voice_tone: str = Field("", description="声音/语气特征 (英文)")
    appearance: str = Field("", description="外貌特征 (英文)")


class CharacterRegistry(BaseModel):
    """角色注册表（全局角色定义，供场景引用）。"""

    characters: list[ScriptCharacter] = Field(default_factory=list)


# ============================================================
# 镜头与对话
# ============================================================


class DialogueLine(BaseModel):
    """对话行。"""

    character: str = Field(..., description="角色英文名")
    line: str = Field(..., description="台词 (英文)")
    emotion: str = Field("", description="情感状态")
    action: str = Field("", description="伴随动作")


class Narration(BaseModel):
    """旁白/叙述。"""

    text: str = Field(..., description="旁白文本 (英文)")
    style: str = Field("neutral", description="叙述风格: neutral/dramatic/poetic/suspenseful")


class ShotLighting(BaseModel):
    """灯光设置。"""

    primary: str = Field("", description="主光: natural/warm/cool/dramatic/dim/neon/backlit")
    mood: str = Field("", description="灯光氛围")
    direction: str = Field("", description="灯光方向: top/front/side/back/silhouette")


class ShotSound(BaseModel):
    """音效设置。"""

    ambient: str = Field("", description="环境音: wind/rain/city/forest/silence")
    effects: list[str] = Field(default_factory=list, description="音效列表: footsteps/door/sword_clash")
    music_mood: str = Field("", description="背景音乐情绪: tense/peaceful/epic/melancholy")


class CameraMovement(BaseModel):
    """镜头运动。"""

    type: str = Field("static", description="运动类型: static/pan/tilt/dolly/tracking/crane/zoom")
    direction: str = Field("", description="方向: left/right/up/in/out")
    speed: str = Field("normal", description="速度: slow/normal/fast")


class Shot(BaseModel):
    """单个镜头。"""

    id: str = Field(..., description="镜头 ID: ch1_s1_sh1")
    camera_angle: str = Field("eye_level", description="机位角度")
    shot_type: str = Field("medium_shot", description="景别")
    frame_description: str = Field("", description="画面描述 (英文)")
    movement: CameraMovement = Field(default_factory=CameraMovement)
    duration_seconds: float = Field(5.0, description="持续时间 (秒)")
    dialogue: list[DialogueLine] = Field(default_factory=list, description="对话")
    narration: Optional[Narration] = Field(None, description="旁白")
    lighting: Optional[ShotLighting] = Field(None, description="灯光")
    sound: Optional[ShotSound] = Field(None, description="音效")
    vfx: str = Field("", description="视觉特效")
    subtitle: str = Field("", description="字幕 (如需要)")


# ============================================================
# 场景
# ============================================================


class SceneTransition(BaseModel):
    """场景转场。"""

    type: str = Field("cut", description="转场类型: cut/fade/dissolve/wipe/match_cut")
    duration_seconds: float = Field(0.0, description="转场时长 (秒)")
    direction: str = Field("", description="方向: in/out")


class Scene(BaseModel):
    """场景。"""

    id: str = Field(..., description="场景 ID: ch1_s1")
    title: str = Field("", description="场景标题 (英文)")
    location: str = Field("", description="地点 (英文)")
    time: str = Field("", description="时间: dawn/morning/afternoon/dusk/night")
    mood: str = Field("", description="氛围")
    tags: list[str] = Field(default_factory=list, description="标签: action/dialogue/flashback")
    summary: str = Field("", description="场景摘要 (英文)")
    transition_in: SceneTransition = Field(default_factory=SceneTransition)
    transition_out: SceneTransition = Field(default_factory=SceneTransition)
    estimated_duration: float = Field(0.0, description="预估时长 (秒)")
    characters_present: list[str] = Field(default_factory=list, description="出场角色英文名")
    continuity_notes: str = Field("", description="连续性备注")
    props: list[str] = Field(default_factory=list, description="道具列表")
    shots: list[Shot] = Field(default_factory=list, description="镜头列表")


# ============================================================
# 章节
# ============================================================


class ChapterMetadata(BaseModel):
    """章节元数据。"""

    number: int = Field(..., description="章节编号")
    title_original: str = Field("", description="原始标题 (中文)")
    title_english: str = Field("", description="英文标题")
    scene_count: int = Field(0, description="场景数")
    shot_count: int = Field(0, description="镜头数")
    estimated_duration: float = Field(0.0, description="预估时长 (秒)")


class ChapterScript(BaseModel):
    """单章脚本。"""

    metadata: ChapterMetadata = Field(..., description="章节元数据")
    scenes: list[Scene] = Field(default_factory=list, description="场景列表")


# ============================================================
# 顶层脚本
# ============================================================


class Script(BaseModel):
    """完整 LRM 脚本（YAML 顶层结构）。

    最终输出的 YAML 文件结构：

    ```yaml
    lrm_script:
      metadata: { ... }
      characters: { ... }
      chapters:
        - metadata: { ... }
          scenes:
            - shots:
                - movement: { ... }
                  dialogue: [ ... ]
    ```
    """

    metadata: ScriptMetadata = Field(default_factory=ScriptMetadata)
    characters: CharacterRegistry = Field(default_factory=CharacterRegistry)
    chapters: list[ChapterScript] = Field(default_factory=list)

    def compute_stats(self) -> ScriptStats:
        """计算并更新统计信息。"""
        total_shots = 0
        total_dialogue = 0
        total_duration = 0.0

        for ch in self.chapters:
            ch_shot_count = 0
            ch_duration = 0.0
            for scene in ch.scenes:
                ch_shot_count += len(scene.shots)
                for shot in scene.shots:
                    total_dialogue += len(shot.dialogue)
                    ch_duration += shot.duration_seconds
            ch.metadata.shot_count = ch_shot_count
            ch.metadata.estimated_duration = ch_duration
            total_shots += ch_shot_count
            total_duration += ch_duration

        self.chapters.sort(key=lambda c: c.metadata.number)

        stats = ScriptStats(
            total_chapters=len(self.chapters),
            total_scenes=sum(len(ch.scenes) for ch in self.chapters),
            total_shots=total_shots,
            total_dialogue_lines=total_dialogue,
            estimated_duration_minutes=round(total_duration / 60, 1),
            estimated_word_count=total_dialogue * 8,  # 粗估
        )
        self.metadata.stats = stats
        return stats

    def to_yaml_dict(self) -> dict:
        """转换为适合 YAML 导出的字典。"""
        return self.model_dump(mode="json", exclude_none=True, exclude_defaults=False)


# ============================================================
# 校验规则
# ============================================================


class ValidationError(BaseModel):
    """校验错误。"""

    level: str = Field("error", description="error/warning")
    path: str = Field("", description="错误路径: chapters[0].scenes[1].shots[0]")
    message: str = Field("", description="错误描述")


def validate_script(script: Script) -> list[ValidationError]:
    """校验脚本结构完整性。

    Returns:
        错误列表（空列表表示通过）。
    """
    errors: list[ValidationError] = []

    # 顶层校验
    if not script.metadata.source_novel:
        errors.append(ValidationError(level="warning", path="metadata.source_novel", message="缺少来源小说名"))

    # 角色校验
    known_names = {c.name for c in script.characters.characters}
    known_english = {c.english_name for c in script.characters.characters if c.english_name}

    # 章节校验
    seen_ids: set[str] = set()
    for ch_idx, ch in enumerate(script.chapters):
        ch_path = f"chapters[{ch_idx}]"

        if ch.metadata.scene_count == 0 and not ch.scenes:
            errors.append(ValidationError(level="warning", path=f"{ch_path}.scenes", message=f"第{ch.metadata.number}章没有场景"))

        for sc_idx, scene in enumerate(ch.scenes):
            sc_path = f"{ch_path}.scenes[{sc_idx}]"

            # ID 唯一性
            if scene.id in seen_ids:
                errors.append(ValidationError(level="error", path=f"{sc_path}.id", message=f"重复 ID: {scene.id}"))
            seen_ids.add(scene.id)

            # 必填字段
            if not scene.title:
                errors.append(ValidationError(level="warning", path=f"{sc_path}.title", message="缺少标题"))
            if not scene.location:
                errors.append(ValidationError(level="warning", path=f"{sc_path}.location", message="缺少地点"))

            # 角色校验
            for char_name in scene.characters_present:
                if char_name not in known_names and char_name not in known_english:
                    errors.append(ValidationError(level="warning", path=f"{sc_path}.characters_present", message=f"未定义角色: {char_name}"))

            # 镜头校验
            for sh_idx, shot in enumerate(scene.shots):
                sh_path = f"{sc_path}.shots[{sh_idx}]"

                if shot.id in seen_ids:
                    errors.append(ValidationError(level="error", path=f"{sh_path}.id", message=f"重复 ID: {shot.id}"))
                seen_ids.add(shot.id)

                if not shot.frame_description:
                    errors.append(ValidationError(level="warning", path=f"{sh_path}.frame_description", message="缺少画面描述"))

                # 对话校验
                for d_idx, dialogue in enumerate(shot.dialogue):
                    if not dialogue.character:
                        errors.append(ValidationError(level="warning", path=f"{sh_path}.dialogue[{d_idx}]", message="缺少角色名"))
                    if not dialogue.line:
                        errors.append(ValidationError(level="warning", path=f"{sh_path}.dialogue[{d_idx}]", message="缺少台词"))

    return errors
