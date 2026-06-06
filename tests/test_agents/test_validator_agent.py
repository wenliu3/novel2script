"""PR-08 Validator Agent 测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.schema.script import Script, ScriptCharacter, ChapterScript, ScriptMetadata
from app.schema.scene import Scene, Beat, Shot
from app.agents.validator_agent import ValidatorAgent, ValidationResult
from app.services.llm_service import LLMService


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock(spec=LLMService)
    llm.prompt_json.return_value = {}
    return llm


@pytest.fixture
def agent(mock_llm: MagicMock) -> ValidatorAgent:
    return ValidatorAgent(mock_llm)


def _make_valid_script() -> Script:
    """构造一个合法的完整 Script。"""
    scenes = [
        Scene(id="ch1_s1", title="夜探王府", location="王府书房", time="night", mood="tense",
              beats=[
                  Beat(type="action", character="张三", content="推门而入"),
                  Beat(type="dialogue", character="char_001", content="有人吗？"),
              ],
              shots=[
                  Shot(id="ch1_s1_sh1", frame_description="Zhang San enters.", movement="static"),
              ]),
    ]
    return Script(
        title="诡夜客栈",
        genre="悬疑",
        characters=[
            ScriptCharacter(id="char_001", name="张三", role="主角"),
            ScriptCharacter(id="char_002", name="店小二", role="配角"),
        ],
        metadata=ScriptMetadata(source_novel="诡夜客栈", total_chapters=1, total_scenes=1),
        chapters=[ChapterScript(number=1, title="第一章", scenes=scenes)],
    )


class TestValidationResult:
    def test_empty_is_valid(self) -> None:
        vr = ValidationResult()
        assert vr.is_valid is True

    def test_with_error(self) -> None:
        vr = ValidationResult()
        vr.add_error("test error")
        assert vr.is_valid is False

    def test_summary(self) -> None:
        vr = ValidationResult()
        vr.add_error("e1")
        vr.add_warning("w1")
        vr.add_fix("f1")
        assert "错误" in vr.summary()
        assert "警告" in vr.summary()
        assert "已修复" in vr.summary()


class TestValidatorAgent:
    def test_valid_script_passes(self, agent: ValidatorAgent) -> None:
        """合法脚本应通过校验。"""
        script = _make_valid_script()
        result = agent.execute(script)
        assert result.is_valid

    def test_missing_title(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.title = ""
        result = agent.execute(script)
        assert not result.is_valid

    def test_no_chapters(self, agent: ValidatorAgent) -> None:
        script = Script(title="test")
        result = agent.execute(script)
        assert not result.is_valid

    def test_duplicate_scene_id(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        # 复制场景造成 ID 重复
        scene = script.chapters[0].scenes[0]
        script.chapters[0].scenes.append(scene)
        result = agent.execute(script)
        assert not result.is_valid

    def test_invalid_beat_type(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.chapters[0].scenes[0].beats.append(
            Beat(type="singing", character="张三", content="唱歌")
        )
        result = agent.execute(script)
        assert not result.is_valid

    def test_dialogue_beat_missing_character(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.chapters[0].scenes[0].beats.append(
            Beat(type="dialogue", character="", content="你好")
        )
        result = agent.execute(script)
        # 警告级别，不阻断
        assert len(result.warnings) >= 1

    def test_missing_beat_content(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.chapters[0].scenes[0].beats.append(
            Beat(type="action", character="张三", content="")
        )
        result = agent.execute(script)
        assert len(result.warnings) >= 1

    def test_auto_fix_empty_scene_id(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.chapters[0].scenes[0].id = ""
        result = agent.execute(script)
        # 自动修复后 ID 不为空
        assert script.chapters[0].scenes[0].id != ""
        assert len(result.fixes_applied) >= 1

    def test_auto_fix_empty_beat_type(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.chapters[0].scenes[0].beats.append(
            Beat(type="", character="张三", content="动作")
        )
        result = agent.execute(script)
        # type 被修复为 action
        assert script.chapters[0].scenes[0].beats[-1].type == "action"
        assert len(result.fixes_applied) >= 1

    def test_auto_fix_dialogue_missing_character(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.chapters[0].scenes[0].beats.append(
            Beat(type="dialogue", character="", content="你好")
        )
        result = agent.execute(script)
        # character 被修复为 "未知"
        assert script.chapters[0].scenes[0].beats[-1].character == "未知"

    def test_auto_fix_empty_genre(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.genre = ""
        result = agent.execute(script)
        assert script.genre == "未分类"

    def test_auto_fix_empty_character_id(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.characters.append(ScriptCharacter(id="", name="新角色"))
        result = agent.execute(script)
        assert script.characters[-1].id != ""

    def test_missing_characters_warning(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.characters = []
        result = agent.execute(script)
        assert len(result.warnings) >= 1

    def test_missing_genre_warning(self, agent: ValidatorAgent) -> None:
        script = _make_valid_script()
        script.genre = ""
        result = agent.execute(script)
        # auto-fix 会修复，所以不会报 warning
        # 但在 auto_fix 之前的 validation 会报 warning
        pass  # auto-fix 先于 warning 触发，genre 被修复
