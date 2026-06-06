"""YAML Schema 定义模块测试。

测试 Schema 数据模型、YAML 导出、校验规则等核心功能。
"""

import pytest
from pathlib import Path

from app.schema.yaml_schema import (
    Script,
    ScriptMetadata,
    ScriptStats,
    ScriptConfig,
    ScriptCharacter,
    CharacterRegistry,
    ChapterScript,
    ChapterMetadata,
    Scene,
    SceneTransition,
    Shot,
    CameraMovement,
    DialogueLine,
    Narration,
    ShotLighting,
    ShotSound,
    ValidationError,
    validate_script,
    YAML_SCHEMA_VERSION,
)
from app.exporters.yaml_exporter import (
    export_yaml,
    export_from_script,
    yaml_to_string,
    validate_yaml_file,
)


# ──────────────────────────────────────
# Schema 数据模型测试
# ──────────────────────────────────────


class TestScriptMetadata:
    """元数据模型测试。"""

    def test_default_metadata(self):
        m = ScriptMetadata()
        assert m.schema_version == "1.0"
        assert m.generator == "novel2script"
        assert m.generated_at  # 非空

    def test_with_config(self):
        m = ScriptMetadata(config=ScriptConfig(model_used="milm"))
        assert m.config.model_used == "milm"

    def test_stats_default(self):
        s = ScriptStats()
        assert s.total_chapters == 0
        assert s.estimated_duration_minutes == 0.0


class TestScriptCharacter:
    """角色定义测试。"""

    def test_create_character(self):
        c = ScriptCharacter(name="克莱恩", english_name="Klein", role="protagonist", importance=10)
        assert c.name == "克莱恩"
        assert c.role == "protagonist"

    def test_defaults(self):
        c = ScriptCharacter(name="路人")
        assert c.importance == 0
        assert c.aliases == []


class TestShot:
    """镜头模型测试。"""

    def test_create_shot(self):
        shot = Shot(
            id="ch1_s1_sh1",
            frame_description="A dark alley",
        )
        assert shot.id == "ch1_s1_sh1"
        assert shot.duration_seconds == 5.0
        assert shot.movement.type == "static"

    def test_shot_with_dialogue(self):
        shot = Shot(
            id="ch1_s1_sh1",
            frame_description="test",
            dialogue=[
                DialogueLine(character="Klein", line="Hello", emotion="calm"),
            ],
        )
        assert len(shot.dialogue) == 1
        assert shot.dialogue[0].character == "Klein"

    def test_shot_with_narration(self):
        shot = Shot(
            id="ch1_s1_sh1",
            frame_description="test",
            narration=Narration(text="Once upon a time...", style="dramatic"),
        )
        assert shot.narration.style == "dramatic"

    def test_shot_with_lighting(self):
        shot = Shot(
            id="ch1_s1_sh1",
            frame_description="test",
            lighting=ShotLighting(primary="warm", mood="cozy", direction="side"),
        )
        assert shot.lighting.primary == "warm"

    def test_shot_with_sound(self):
        shot = Shot(
            id="ch1_s1_sh1",
            frame_description="test",
            sound=ShotSound(ambient="rain", effects=["thunder"], music_mood="tense"),
        )
        assert shot.sound.ambient == "rain"
        assert "thunder" in shot.sound.effects


class TestSceneTransition:
    """转场模型测试。"""

    def test_default_transition(self):
        t = SceneTransition()
        assert t.type == "cut"

    def test_fade_transition(self):
        t = SceneTransition(type="fade", duration_seconds=1.5, direction="in")
        assert t.duration_seconds == 1.5


class TestScene:
    """场景模型测试。"""

    def test_create_scene(self):
        scene = Scene(
            id="ch1_s1",
            title="The Awakening",
            location="Dark basement",
            time="night",
            mood="mysterious",
        )
        assert scene.id == "ch1_s1"
        assert scene.tags == []

    def test_scene_with_shots(self):
        scene = Scene(
            id="ch1_s1",
            title="Test",
            location="Room",
            shots=[
                Shot(id="ch1_s1_sh1", frame_description="a"),
                Shot(id="ch1_s1_sh2", frame_description="b"),
            ],
        )
        assert len(scene.shots) == 2


class TestChapterScript:
    """章节脚本测试。"""

    def test_create_chapter(self):
        ch = ChapterScript(
            metadata=ChapterMetadata(number=1, title_original="第一章", title_english="Chapter 1"),
            scenes=[Scene(id="ch1_s1", title="Test", location="Room")],
        )
        assert ch.metadata.number == 1
        assert len(ch.scenes) == 1


# ──────────────────────────────────────
# Script 顶层模型测试
# ──────────────────────────────────────


class TestScript:
    """Script 顶层模型测试。"""

    def _make_script(self) -> Script:
        """创建测试用的完整 Script 对象。"""
        return Script(
            metadata=ScriptMetadata(source_novel="测试小说"),
            characters=CharacterRegistry(characters=[
                ScriptCharacter(name="张三", english_name="Zhang", role="protagonist", importance=9),
                ScriptCharacter(name="李四", english_name="Li", role="supporting", importance=5),
            ]),
            chapters=[
                ChapterScript(
                    metadata=ChapterMetadata(number=1, title_original="第一章"),
                    scenes=[
                        Scene(
                            id="ch1_s1",
                            title="Opening",
                            location="Forest",
                            characters_present=["Zhang"],
                            shots=[
                                Shot(id="ch1_s1_sh1", frame_description="Forest view",
                                     duration_seconds=5.0,
                                     dialogue=[DialogueLine(character="Zhang", line="Hello")]),
                                Shot(id="ch1_s1_sh2", frame_description="Close up",
                                     duration_seconds=3.0),
                            ],
                        ),
                        Scene(
                            id="ch1_s2",
                            title="Meeting",
                            location="Village",
                            characters_present=["Zhang", "Li"],
                            shots=[
                                Shot(id="ch1_s2_sh1", frame_description="Village",
                                     duration_seconds=4.0,
                                     dialogue=[
                                         DialogueLine(character="Zhang", line="Hi"),
                                         DialogueLine(character="Li", line="Bye"),
                                     ]),
                            ],
                        ),
                    ],
                ),
            ],
        )

    def test_compute_stats(self):
        script = self._make_script()
        stats = script.compute_stats()
        assert stats.total_chapters == 1
        assert stats.total_scenes == 2
        assert stats.total_shots == 3
        assert stats.total_dialogue_lines == 3
        assert stats.estimated_duration_minutes > 0

    def test_to_yaml_dict(self):
        script = self._make_script()
        d = script.to_yaml_dict()
        assert "metadata" in d
        assert "characters" in d
        assert "chapters" in d
        assert d["metadata"]["schema_version"] == "1.0"

    def test_empty_script(self):
        script = Script()
        stats = script.compute_stats()
        assert stats.total_chapters == 0


# ──────────────────────────────────────
# 校验规则测试
# ──────────────────────────────────────


class TestValidation:
    """脚本校验测试。"""

    def test_valid_script(self):
        script = Script(
            metadata=ScriptMetadata(source_novel="测试"),
            characters=CharacterRegistry(characters=[
                ScriptCharacter(name="张三", english_name="Zhang"),
            ]),
            chapters=[ChapterScript(
                metadata=ChapterMetadata(number=1),
                scenes=[Scene(
                    id="ch1_s1", title="Scene 1", location="Room",
                    characters_present=["Zhang"],
                    shots=[Shot(id="ch1_s1_sh1", frame_description="test",
                                dialogue=[DialogueLine(character="Zhang", line="Hi")])],
                )],
            )],
        )
        errors = validate_script(script)
        assert len(errors) == 0

    def test_missing_title(self):
        script = Script(
            chapters=[ChapterScript(
                metadata=ChapterMetadata(number=1),
                scenes=[Scene(id="ch1_s1", location="Room",
                              shots=[Shot(id="sh1", frame_description="t")])],
            )],
        )
        errors = validate_script(script)
        assert any("缺少标题" in e.message for e in errors)

    def test_missing_location(self):
        script = Script(
            chapters=[ChapterScript(
                metadata=ChapterMetadata(number=1),
                scenes=[Scene(id="ch1_s1", title="Test",
                              shots=[Shot(id="sh1", frame_description="t")])],
            )],
        )
        errors = validate_script(script)
        assert any("缺少地点" in e.message for e in errors)

    def test_duplicate_id(self):
        script = Script(
            chapters=[ChapterScript(
                metadata=ChapterMetadata(number=1),
                scenes=[
                    Scene(id="ch1_s1", title="A", location="X",
                          shots=[Shot(id="sh1", frame_description="t")]),
                    Scene(id="ch1_s1", title="B", location="Y",
                          shots=[Shot(id="sh2", frame_description="t")]),
                ],
            )],
        )
        errors = validate_script(script)
        assert any("重复 ID" in e.message for e in errors)

    def test_undefined_character(self):
        script = Script(
            characters=CharacterRegistry(),
            chapters=[ChapterScript(
                metadata=ChapterMetadata(number=1),
                scenes=[Scene(id="ch1_s1", title="T", location="L",
                              characters_present=["Ghost"],
                              shots=[Shot(id="sh1", frame_description="t")])],
            )],
        )
        errors = validate_script(script)
        assert any("未定义角色" in e.message for e in errors)


# ──────────────────────────────────────
# YAML 导出测试
# ──────────────────────────────────────


class TestYAMLExport:
    """YAML 导出功能测试。"""

    def _make_script(self) -> Script:
        return Script(
            metadata=ScriptMetadata(source_novel="测试"),
            characters=CharacterRegistry(characters=[
                ScriptCharacter(name="克莱恩", english_name="Klein", role="protagonist"),
            ]),
            chapters=[ChapterScript(
                metadata=ChapterMetadata(number=1, title_original="第一章", title_english="Chapter 1"),
                scenes=[Scene(
                    id="ch1_s1", title="Test Scene", location="Room",
                    time="night", mood="tense",
                    transition_in=SceneTransition(type="fade", duration_seconds=1.5),
                    shots=[
                        Shot(id="ch1_s1_sh1", frame_description="A dark room",
                             movement=CameraMovement(type="dolly", direction="in", speed="slow"),
                             duration_seconds=5.0,
                             lighting=ShotLighting(primary="dim"),
                             sound=ShotSound(ambient="silence"),
                             dialogue=[DialogueLine(character="Klein", line="Hello", emotion="nervous")]),
                    ],
                )],
            )],
        )

    def test_export_yaml(self, tmp_path):
        script = self._make_script()
        path = export_from_script(script, tmp_path, "test.yaml")
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "LRM Script" in content
        assert "克莱恩" in content
        assert "Klein" in content

    def test_yaml_valid(self, tmp_path):
        script = self._make_script()
        path = export_from_script(script, tmp_path, "test.yaml")
        is_valid, _ = validate_yaml_file(path)
        assert is_valid

    def test_yaml_to_string(self):
        script = self._make_script()
        yaml_str = yaml_to_string(script)
        assert "克莱恩" in yaml_str
        assert "fade" in yaml_str

    def test_enum_in_yaml(self, tmp_path):
        """Enum 值应被正确序列化为字符串。"""
        script = self._make_script()
        path = export_from_script(script, tmp_path, "test.yaml")
        content = path.read_text(encoding="utf-8")
        assert "protagonist" in content
        assert "dim" in content

    def test_multiline_preserved(self, tmp_path):
        """多行文本应使用 | 块格式。"""
        script = Script(
            chapters=[ChapterScript(
                metadata=ChapterMetadata(number=1),
                scenes=[Scene(
                    id="ch1_s1", title="Test", location="Room",
                    continuity_notes="Line 1\nLine 2\nLine 3",
                    shots=[Shot(id="sh1", frame_description="test",
                                narration=Narration(text="Line A\nLine B\nLine C"))],
                )],
            )],
        )
        path = export_from_script(script, tmp_path, "test.yaml")
        content = path.read_text(encoding="utf-8")
        assert "|" in content  # 块格式标记

    def test_file_header(self, tmp_path):
        """导出文件应包含注释头。"""
        script = Script()
        path = export_from_script(script, tmp_path, "test.yaml")
        content = path.read_text(encoding="utf-8")
        assert content.startswith("#")


# ──────────────────────────────────────
# Schema 版本测试
# ──────────────────────────────────────


class TestSchemaVersion:
    """Schema 版本号测试。"""

    def test_version_format(self):
        assert YAML_SCHEMA_VERSION == "1.0"
        parts = YAML_SCHEMA_VERSION.split(".")
        assert len(parts) == 2

    def test_metadata_has_version(self):
        m = ScriptMetadata()
        assert m.schema_version == YAML_SCHEMA_VERSION
