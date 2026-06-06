"""PR-05 对白生成 Agent 测试。

覆盖：Beat 模型 / Scene.beats / DialogueAgent 节拍+镜头生成 / 异常降级
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.schema.scene import Beat, Scene, Shot
from app.agents.dialogue_agent import DialogueAgent
from app.services.llm_service import LLMService


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock(spec=LLMService)
    llm.prompt_json.return_value = _mock_response()
    return llm


@pytest.fixture
def agent(mock_llm: MagicMock) -> DialogueAgent:
    return DialogueAgent(mock_llm)


@pytest.fixture
def scene() -> Scene:
    return Scene(id="ch1_s1", title="夜探王府", location="王府书房", time="night", mood="tense")


@pytest.fixture
def text() -> str:
    return '张三推开书房门，紧张地环顾四周。"这里果然有问题。"他低声自语。忽然门外传来脚步声，张三迅速吹灭烛台。'


# ── Beat 模型 ──


class TestBeatModel:
    def test_action(self) -> None:
        b = Beat(type="action", character="张三", content="推门而入")
        assert b.type == "action"

    def test_dialogue(self) -> None:
        b = Beat(type="dialogue", character="张三", content="有人吗？")
        assert b.type == "dialogue"

    def test_narration(self) -> None:
        b = Beat(type="narration", character="", content="夜深人静。")
        assert b.type == "narration"

    def test_serialize(self) -> None:
        d = Beat(type="action", character="A", content="test").model_dump()
        assert d["type"] == "action"


# ── Scene.beats ──


class TestSceneBeats:
    def test_filter(self) -> None:
        s = Scene(id="s1", title="t")
        s.beats = [
            Beat(type="action", character="A", content="a"),
            Beat(type="dialogue", character="B", content="d"),
            Beat(type="action", character="A", content="a2"),
            Beat(type="narration", character="", content="n"),
        ]
        assert len(s.action_beats) == 2
        assert len(s.dialogue_beats) == 1

    def test_empty(self) -> None:
        s = Scene(id="s1", title="t")
        assert s.action_beats == []
        assert s.dialogue_beats == []


# ── DialogueAgent ──


class TestDialogueAgent:
    def test_execute_generates_beats(self, agent: DialogueAgent, scene: Scene, text: str, mock_llm: MagicMock) -> None:
        result = agent.execute(scene, text, chapter_number=1, character_names=["张三"])
        assert len(result.beats) > 0
        types = {b.type for b in result.beats}
        assert "action" in types
        assert "dialogue" in types
        mock_llm.prompt_json.assert_called_once()

    def test_generate_beats_method(self, agent: DialogueAgent, scene: Scene, text: str) -> None:
        beats = agent.generate_beats(scene, text, character_names=["张三"])
        assert len(beats) > 0
        assert all(isinstance(b, Beat) for b in beats)

    def test_llm_error_graceful(self, mock_llm: MagicMock, scene: Scene, text: str) -> None:
        mock_llm.prompt_json.side_effect = RuntimeError("timeout")
        agent = DialogueAgent(mock_llm)
        result = agent.execute(scene, text, chapter_number=1)
        assert result.id == scene.id
        assert result.beats == []

    def test_execute_generates_shots(self, agent: DialogueAgent, scene: Scene, text: str) -> None:
        result = agent.execute(scene, text, chapter_number=1)
        assert len(result.shots) > 0
        assert isinstance(result.shots[0], Shot)


def _mock_response() -> dict:
    return {
        "beats": [
            {"type": "action", "character": "张三", "content": "张三推开书房门，紧张环顾四周。"},
            {"type": "dialogue", "character": "张三", "content": "这里果然有问题。"},
            {"type": "action", "character": "张三", "content": "张三迅速吹灭烛台躲藏。"},
            {"type": "narration", "character": "", "content": "门外脚步声越来越近。"},
        ],
        "shots": [
            {
                "camera_angle": "eye_level", "shot_type": "medium_shot",
                "frame_description": "Zhang San enters the dark study.",
                "movement": "tracking", "duration_seconds": 6,
                "dialogue": [],
                "narration": "", "visual_effects": "",
            },
            {
                "camera_angle": "eye_level", "shot_type": "close_up",
                "frame_description": "Zhang San whispers to himself.",
                "movement": "static", "duration_seconds": 4,
                "dialogue": [
                    {"character": "Zhang San", "line": "Something's wrong here...", "emotion": "tense"}
                ],
                "narration": "", "visual_effects": "",
            },
        ],
    }
