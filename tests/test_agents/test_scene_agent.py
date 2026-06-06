"""场景规划 Agent 测试。

测试场景模型、拆分逻辑、转场设计、连续性追踪、时长估算等核心功能。
LLM 相关测试标记为 slow 跳过。
"""

import pytest
from app.schema.scene import (
    Scene,
    ScenePlan,
    Shot,
    DialogueLine,
    ShotType,
    CameraAngle,
    CameraMovement,
    TransitionType,
    SceneTag,
)
from app.agents.scene_agent import SceneAgent, estimate_scene_count


# ──────────────────────────────────────
# 场景数据模型测试
# ──────────────────────────────────────


class TestSceneModel:
    """场景模型基础测试。"""

    def test_create_scene(self):
        """创建场景对象。"""
        scene = Scene(
            id="ch1_s1",
            title="The Encounter",
            location="Mountain Path",
            time="morning",
            mood="tense",
        )
        assert scene.id == "ch1_s1"
        assert scene.title == "The Encounter"
        assert scene.time == "morning"

    def test_scene_defaults(self):
        """默认值应正确。"""
        scene = Scene(id="ch1_s1")
        assert scene.location == ""
        assert scene.tags == []
        assert scene.transition_in == "cut"
        assert scene.transition_out == "cut"
        assert scene.shots == []
        assert scene.characters_present == []

    def test_scene_total_duration_from_shots(self):
        """无 estimated_duration 时应累加镜头时长。"""
        scene = Scene(
            id="ch1_s1",
            shots=[
                Shot(id="sh1", camera_angle="eye_level", shot_type="medium_shot",
                     frame_description="test", duration_seconds=5.0),
                Shot(id="sh2", camera_angle="low_angle", shot_type="close_up",
                     frame_description="test", duration_seconds=3.0),
            ],
        )
        assert scene.total_duration == 8.0

    def test_scene_total_duration_estimated(self):
        """有 estimated_duration 时应优先使用。"""
        scene = Scene(
            id="ch1_s1",
            estimated_duration=30.0,
            shots=[
                Shot(id="sh1", camera_angle="eye_level", shot_type="medium_shot",
                     frame_description="test", duration_seconds=5.0),
            ],
        )
        assert scene.total_duration == 30.0

    def test_scene_shot_count(self):
        scene = Scene(id="ch1_s1", shots=[
            Shot(id="sh1", camera_angle="", shot_type="", frame_description="a"),
            Shot(id="sh2", camera_angle="", shot_type="", frame_description="b"),
            Shot(id="sh3", camera_angle="", shot_type="", frame_description="c"),
        ])
        assert scene.shot_count == 3

    def test_scene_dialogue_count(self):
        scene = Scene(id="ch1_s1", shots=[
            Shot(id="sh1", camera_angle="", shot_type="", frame_description="a",
                 dialogue=[
                     DialogueLine(character="A", line="Hello"),
                     DialogueLine(character="B", line="Hi"),
                 ]),
            Shot(id="sh2", camera_angle="", shot_type="", frame_description="b",
                 dialogue=[
                     DialogueLine(character="A", line="Bye"),
                 ]),
        ])
        assert scene.dialogue_count == 3

    def test_scene_has_tag(self):
        scene = Scene(id="ch1_s1", tags=["action", "dialogue"])
        assert scene.has_tag("action") is True
        assert scene.has_tag("narration") is False


# ──────────────────────────────────────
# ScenePlan 测试
# ──────────────────────────────────────


class TestScenePlan:
    """场景规划结果测试。"""

    def test_validate_valid_plan(self):
        plan = ScenePlan(
            chapter_number=1,
            scenes=[
                Scene(id="ch1_s1", title="Opening", location="Forest"),
                Scene(id="ch1_s2", title="Battle", location="Cave"),
            ],
        )
        errors = plan.validate_structure()
        assert len(errors) == 0

    def test_validate_empty_scenes(self):
        plan = ScenePlan(chapter_number=1, scenes=[])
        errors = plan.validate_structure()
        assert len(errors) == 1
        assert "没有场景" in errors[0]

    def test_validate_missing_title(self):
        plan = ScenePlan(
            chapter_number=1,
            scenes=[Scene(id="ch1_s1", location="Forest")],
        )
        errors = plan.validate_structure()
        assert any("缺少标题" in e for e in errors)

    def test_validate_missing_location(self):
        plan = ScenePlan(
            chapter_number=1,
            scenes=[Scene(id="ch1_s1", title="Test")],
        )
        errors = plan.validate_structure()
        assert any("缺少地点" in e for e in errors)


# ──────────────────────────────────────
# 枚举类型测试
# ──────────────────────────────────────


class TestSceneEnums:
    """场景相关枚举测试。"""

    def test_shot_types(self):
        assert ShotType.CLOSE_UP.value == "close_up"
        assert ShotType.WIDE_SHOT.value == "wide_shot"
        assert len(ShotType) == 8

    def test_camera_angles(self):
        assert CameraAngle.EYE_LEVEL.value == "eye_level"
        assert CameraAngle.BIRD_EYE.value == "bird_eye"
        assert len(CameraAngle) == 6

    def test_transitions(self):
        assert TransitionType.CUT.value == "cut"
        assert TransitionType.MATCH_CUT.value == "match_cut"
        assert len(TransitionType) == 8

    def test_scene_tags(self):
        assert SceneTag.ACTION.value == "action"
        assert SceneTag.FLASHBACK.value == "flashback"
        assert len(SceneTag) == 9


# ──────────────────────────────────────
# 场景数量预估测试
# ──────────────────────────────────────


class TestSceneCountEstimation:
    """场景数量预估测试。"""

    def test_short_text(self):
        assert estimate_scene_count(500) == 1

    def test_medium_text(self):
        assert estimate_scene_count(5000) == 3

    def test_long_text(self):
        assert estimate_scene_count(15000) == 6

    def test_very_long_text(self):
        assert estimate_scene_count(25000) == 8


# ──────────────────────────────────────
# 镜头模型测试
# ──────────────────────────────────────


class TestShotModel:
    """镜头模型测试。"""

    def test_create_shot(self):
        shot = Shot(
            id="ch1_s1_sh1",
            camera_angle="low_angle",
            shot_type="close_up",
            frame_description="A sword gleaming in moonlight",
            movement="static",
            duration_seconds=5.0,
        )
        assert shot.id == "ch1_s1_sh1"
        assert shot.movement == "static"

    def test_shot_defaults(self):
        shot = Shot(id="sh1", camera_angle="", shot_type="", frame_description="")
        assert shot.duration_seconds == 5.0
        assert shot.dialogue == []
        assert shot.narration == ""
        assert shot.visual_effects == ""
        assert shot.sound_effects == ""
        assert shot.lighting == ""

    def test_dialogue_line(self):
        dl = DialogueLine(
            character="Klein",
            line="I need to be careful.",
            emotion="cautious",
            action="clenches fist",
        )
        assert dl.character == "Klein"
        assert dl.action == "clenches fist"


# ──────────────────────────────────────
# SceneAgent 文本切分测试（不需要 LLM）
# ──────────────────────────────────────


class TestSceneAgentInternal:
    """Agent 内部逻辑测试（不需要 LLM 连接）。"""

    def test_estimate_duration_action(self):
        """动作戏场景应有较短的预估时长。"""
        agent = SceneAgent.__new__(SceneAgent)
        scene = Scene(id="ch1_s1", tags=["action"], shots=[
            Shot(id=f"sh{i}", camera_angle="", shot_type="", frame_description="a")
            for i in range(5)
        ])
        duration = agent._estimate_duration(scene)
        assert duration == 20.0  # 5 shots * 4s

    def test_estimate_duration_dialogue(self):
        """对话戏场景时长应适中。"""
        agent = SceneAgent.__new__(SceneAgent)
        scene = Scene(id="ch1_s1", tags=["dialogue"], shots=[
            Shot(id=f"sh{i}", camera_angle="", shot_type="", frame_description="a")
            for i in range(4)
        ])
        duration = agent._estimate_duration(scene)
        assert duration >= 20.0  # 4 shots * 5s minimum

    def test_estimate_duration_narration(self):
        """旁白场景应有较长的预估时长。"""
        agent = SceneAgent.__new__(SceneAgent)
        scene = Scene(id="ch1_s1", tags=["narration"], shots=[
            Shot(id=f"sh{i}", camera_angle="", shot_type="", frame_description="a")
            for i in range(3)
        ])
        duration = agent._estimate_duration(scene)
        assert duration == 24.0  # 3 shots * 8s

    def test_post_process_first_scene_fade_in(self):
        """第一个场景应默认淡入。"""
        agent = SceneAgent.__new__(SceneAgent)
        scenes = [
            Scene(id="ch1_s1", transition_in="cut"),
            Scene(id="ch1_s2", transition_in="cut"),
        ]
        result = agent._post_process(scenes, 1)
        assert result[0].transition_in == "fade_in"

    def test_post_process_last_scene_fade_out(self):
        """最后一个场景应默认淡出。"""
        agent = SceneAgent.__new__(SceneAgent)
        scenes = [
            Scene(id="ch1_s1", transition_out="cut"),
            Scene(id="ch1_s2", transition_out="cut"),
        ]
        result = agent._post_process(scenes, 1)
        assert result[-1].transition_out == "fade_out"

    def test_post_process_preserves_custom_transitions(self):
        """自定义转场不应被覆盖。"""
        agent = SceneAgent.__new__(SceneAgent)
        scenes = [
            Scene(id="ch1_s1", transition_in="fade_in", transition_out="dissolve"),
            Scene(id="ch1_s2", transition_in="match_cut", transition_out="cut"),
        ]
        result = agent._post_process(scenes, 1)
        assert result[0].transition_out == "dissolve"
        assert result[1].transition_in == "match_cut"
        assert result[1].transition_out == "fade_out"

    def test_post_process_estimates_duration(self):
        """无时长的场景应被自动估算。"""
        agent = SceneAgent.__new__(SceneAgent)
        scenes = [Scene(id="ch1_s1", tags=["dialogue"], shots=[
            Shot(id="sh1", camera_angle="", shot_type="", frame_description="a"),
            Shot(id="sh2", camera_angle="", shot_type="", frame_description="b"),
            Shot(id="sh3", camera_angle="", shot_type="", frame_description="c"),
        ])]
        result = agent._post_process(scenes, 1)
        assert result[0].estimated_duration > 0

    def test_track_continuity(self):
        """角色连续性追踪应正确记录。"""
        agent = SceneAgent.__new__(SceneAgent)
        scenes = [
            Scene(id="ch1_s1", characters_present=["Klein", "Dunn"]),
            Scene(id="ch1_s2", characters_present=["Klein"]),  # Dunn 离开
            Scene(id="ch1_s3", characters_present=["Klein", "Melissa"]),  # Melissa 加入
        ]
        agent._track_continuity(scenes)
        assert "离开" in scenes[1].continuity_notes
        assert "加入" in scenes[2].continuity_notes


# ──────────────────────────────────────
# LLM 集成测试（需要 API 连接，默认跳过）
# ──────────────────────────────────────


@pytest.mark.slow
class TestSceneAgentLLM:
    """需要真实 LLM 连接的测试。"""

    def test_split_scenes(self):
        """从文本中拆分场景。"""
        from app.services.config import load_settings
        from app.services.llm_service import LLMService

        try:
            settings = load_settings()
        except ValueError:
            pytest.skip("未配置 MILM_API_KEY，跳过 LLM 测试")

        llm = LLMService(settings)
        agent = SceneAgent(llm)

        text = """第一章 山中相遇

清晨，阳光洒在山间小路上。少年背着包裹，独自走在下山的路上。

他来到一个小镇，镇上人来人往，非常热闹。少年找了一家客栈住下。

晚上，少年在客栈里遇到了一位白发老者。老者说："年轻人，你骨骼清奇。"

少年惊讶地看着老者，不知道该说什么好。"""

        scenes = agent.execute(
            chapter_text=text,
            chapter_number=1,
            character_names=["少年", "白发老者"],
        )

        assert len(scenes) >= 2
        assert scenes[0].transition_in == "fade_in"  # 第一个场景淡入
        assert scenes[-1].transition_out == "fade_out"  # 最后一个场景淡出
        for scene in scenes:
            assert scene.id.startswith("ch1_s")
            assert scene.estimated_duration > 0
