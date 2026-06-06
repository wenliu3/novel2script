"""测试（适配新架构：单次 LLM 调用 + 断点续传 + 滑动窗口）。"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from app.models import (
    Action,
    Character,
    CharacterList,
    CharacterRelation,
    CharacterRole,
    Chapter,
    DialogueLine,
    Scene,
    Screenplay,
    fix_llm_data,
)
from app.core.splitter import TextSplitter, smart_split, has_chapter_structure, clean_text
from app.core.agent import ScriptAgent, _strip_yaml_fence, _try_parse_yaml
from app.core.builder import export_yaml
from app.core.pipeline import _merge_results
from app.llm import LLM


# ═══════════════════════════════════════════════════════════════
# Models 测试
# ═══════════════════════════════════════════════════════════════


class TestModels:
    def test_character_creation(self):
        c = Character(name="张三", importance=8, role=CharacterRole.PROTAGONIST)
        assert c.name == "张三"
        assert c.importance == 8

    def test_character_list_merge(self):
        list1 = CharacterList(characters=[
            Character(name="张三", importance=5, gender="男"),
        ])
        list2 = CharacterList(characters=[
            Character(name="张三", importance=8, personality="Brave"),
            Character(name="李四", importance=3),
        ])
        merged = list1.merge(list2)
        assert len(merged.characters) == 2
        zhang = merged.find_by_name("张三")
        assert zhang.importance == 8
        assert zhang.gender == "男"
        assert zhang.personality == "Brave"

    def test_character_find_by_alias(self):
        cl = CharacterList(characters=[
            Character(name="张三", aliases=["三哥", "老张"]),
        ])
        assert cl.find_by_name("三哥") is not None
        assert cl.find_by_name("不存在") is None

    def test_merge_first_appearance_both_zero(self):
        """两个角色 first_appearance 都是 0 时，合并后应为 0（非 99999）。"""
        a = Character(name="张三", first_appearance=0)
        b = Character(name="张三", first_appearance=0)
        merged = CharacterList(characters=[a]).merge(CharacterList(characters=[b]))
        assert merged.find_by_name("张三").first_appearance == 0

    def test_merge_first_appearance_one_nonzero(self):
        """一个角色有 first_appearance，合并后取较小值。"""
        a = Character(name="张三", first_appearance=0)
        b = Character(name="张三", first_appearance=3)
        merged = CharacterList(characters=[a]).merge(CharacterList(characters=[b]))
        assert merged.find_by_name("张三").first_appearance == 3

    def test_action_has_type_field(self):
        """Action 模型有 type 字段，默认值为 'action'。"""
        a = Action(text="走进教室")
        assert a.type == "action"

    def test_dialogue_has_type_field(self):
        """DialogueLine 模型有 type 字段，默认值为 'dialogue'。"""
        d = DialogueLine(character="张三", text="你好")
        assert d.type == "dialogue"

    def test_screenplay_creation(self):
        sp = Screenplay(
            title="测试剧本",
            genre="武侠",
            characters={"张三": "主角"},
            chapters=[Chapter(
                chapter_number=1,
                title="第一章",
                scenes=[Scene(
                    scene_number=1,
                    heading="内景 教室 - 白天",
                    location="教室",
                    time_of_day="白天",
                    int_ext="内景",
                    content=[
                        Action(text="张三走进教室"),
                        DialogueLine(character="张三", text="大家好"),
                    ],
                )],
            )],
        )
        assert sp.total_scenes == 1
        assert sp.total_characters == 1
        assert len(sp.chapters[0].scenes[0].content) == 2

    def test_screenplay_from_yaml_with_type_field(self):
        """从 LLM 输出的 YAML（含 type 字段）正确解析。"""
        data = yaml.safe_load(SAMPLE_YAML)
        sp = Screenplay(**data)
        assert sp.title == "测试小说"
        assert sp.chapters[0].scenes[0].content[0].type == "action"
        assert sp.chapters[0].scenes[0].content[1].type == "dialogue"
        assert sp.chapters[0].scenes[0].content[1].character == "张三"

    def test_fix_llm_data_title_as_heading(self):
        """LLM 用 title 代替 heading → 自动修复。"""
        data = {
            "chapters": [{
                "chapter_number": 1,
                "scenes": [{"scene_number": 1, "title": "内景 客栈 - 白天"}],
            }],
        }
        fixed = fix_llm_data(data)
        sp = Screenplay(**fixed)
        assert sp.chapters[0].scenes[0].heading == "内景 客栈 - 白天"

    def test_fix_llm_data_missing_title(self):
        """LLM 没输出 title → 自动补默认值。"""
        data = {"chapters": [{"chapter_number": 1, "scenes": []}]}
        fixed = fix_llm_data(data)
        sp = Screenplay(**fixed)
        assert sp.title == "未命名剧本"

    def test_fix_llm_data_no_chapters(self):
        """LLM 没输出 chapters → 返回空 chapters。"""
        data = {"title": "test"}
        fixed = fix_llm_data(data)
        sp = Screenplay(**fixed)
        assert sp.chapters == []

    def test_fix_llm_data_scenes_as_content(self):
        """LLM 把内容放在 description 字段 → 自动转为 content。"""
        data = {
            "chapters": [{
                "chapter_number": 1,
                "scenes": [{
                    "scene_number": 1,
                    "heading": "场景1",
                    "description": "叶凡走进客栈",
                }],
            }],
        }
        fixed = fix_llm_data(data)
        sp = Screenplay(**fixed)
        assert len(sp.chapters[0].scenes[0].content) == 1

    def test_validate_with_llm_style_output(self):
        """模拟真实 LLM 输出（缺字段）→ 校验通过。"""
        llm_yaml = """title: 遮天
chapters:
  - chapter_number: 1
    chapter_title: 第001章
    scenes:
      - scene_number: 1
        title: 宇宙深处
        description: 九龙拉棺
      - scene_number: 2
        title: 泰山
        description: 众人攀登"""
        sp, err = ScriptAgent.validate_screenplay(llm_yaml)
        assert sp is not None
        assert err is None
        assert sp.title == "遮天"
        assert len(sp.chapters) == 1
        assert len(sp.chapters[0].scenes) == 2


# ═══════════════════════════════════════════════════════════════
# Splitter 测试
# ═══════════════════════════════════════════════════════════════


class TestSplitter:
    def test_short_text_no_split(self):
        splitter = TextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split("短文本")
        assert len(chunks) == 1
        assert chunks[0].is_first and chunks[0].is_last

    def test_long_text_split(self):
        text = "测试内容。" * 10000
        splitter = TextSplitter(chunk_size=5000, chunk_overlap=200)
        chunks = splitter.split(text)
        assert len(chunks) > 1

    def test_empty_text(self):
        assert TextSplitter().split("") == []
        assert TextSplitter().split("  ") == []

    def test_overlap_error(self):
        with pytest.raises(ValueError):
            TextSplitter(chunk_size=100, chunk_overlap=200)

    def test_chapter_detection(self):
        text = "第一章 风起\n内容一\n\n第二章 云涌\n内容二\n\n第三章 雷动\n内容三\n"
        assert has_chapter_structure(text) is True
        assert has_chapter_structure("没有章节的文本" * 100) is False

    def test_smart_split_with_chapters(self):
        text = "第一章 A\n" + "内容。" * 500 + "\n\n第二章 B\n" + "内容。" * 500
        chunks = smart_split(text, chunk_size=5000)
        assert len(chunks) >= 2

    def test_smart_split_without_chapters(self):
        text = "无章节文本。" * 10000
        chunks = smart_split(text, chunk_size=5000)
        assert len(chunks) > 1

    def test_clean_text(self):
        result = clean_text("  hello  \r\n\r\n\r\n  world  ")
        assert "hello" in result
        assert "world" in result
        assert "\r" not in result


# ═══════════════════════════════════════════════════════════════
# ScriptAgent 测试（Mock LLM）
# ═══════════════════════════════════════════════════════════════

SAMPLE_YAML = """\
title: 测试小说
author: 测试作者
genre: 武侠
characters:
  张三: 主角，剑客
  李四: 配角，商人
chapters:
  - chapter_number: 1
    title: 第一章 风起
    scenes:
      - scene_number: 1
        heading: "内景 客栈 - 白天"
        int_ext: 内景
        location: 客栈
        time_of_day: 白天
        characters:
          - 张三
          - 李四
        summary: 张三与李四在客栈相遇
        content:
          - type: action
            text: 张三推门进入客栈
          - type: dialogue
            character: 张三
            text: 小二，来壶酒
"""


class TestScriptAgent:
    def test_convert_chunk(self):
        """转换：单次 LLM 调用，返回 YAML 字符串。"""
        llm = MagicMock(spec=LLM)
        llm.chat.return_value = SAMPLE_YAML
        agent = ScriptAgent(llm)

        result = agent.convert_chunk("张三走进客栈...", chapter_title="第001章 客栈")
        assert "张三" in result
        assert "chapters" in result
        llm.chat.assert_called_once()
        # 验证 prompt 包含原文章节标题
        call_args = llm.chat.call_args
        prompt = call_args[0][0]
        assert "第001章 客栈" in prompt

    def test_validate_screenplay_valid(self):
        """校验通过。"""
        sp, err = ScriptAgent.validate_screenplay(SAMPLE_YAML)
        assert sp is not None
        assert err is None
        assert sp.title == "测试小说"

    def test_validate_screenplay_missing_chapters(self):
        """缺少 chapters 字段 → 校验失败。"""
        sp, err = ScriptAgent.validate_screenplay("title: test\n")
        assert sp is None
        assert err is not None

    def test_validate_screenplay_garbage(self):
        """完全无效的 YAML → 校验失败。"""
        sp, err = ScriptAgent.validate_screenplay("not yaml: [invalid")
        assert sp is None
        assert err is not None


# ═══════════════════════════════════════════════════════════════
# Agent 工具函数测试
# ═══════════════════════════════════════════════════════════════


class TestAgentUtils:
    def test_strip_yaml_fence(self):
        assert _strip_yaml_fence("```yaml\ntitle: test\n```") == "title: test"
        assert _strip_yaml_fence("title: test") == "title: test"

    def test_try_parse_yaml_valid(self):
        data = _try_parse_yaml("title: test\nchapters: []")
        assert data is not None
        assert data["title"] == "test"

    def test_try_parse_yaml_with_tab(self):
        data = _try_parse_yaml("title: test\nchapters:\n\t- chapter_number: 1")
        assert data is not None

    def test_try_parse_yaml_chinese_colon(self):
        data = _try_parse_yaml("title：测试\nchapters: []")
        assert data is not None
        assert "title" in data

    def test_try_parse_yaml_invalid(self):
        assert _try_parse_yaml("not yaml: [invalid") is None


# ═══════════════════════════════════════════════════════════════
# Builder 测试
# ═══════════════════════════════════════════════════════════════


class TestBuilder:
    def test_export_yaml(self):
        screenplay = Screenplay(
            title="测试剧本",
            genre="武侠",
            characters={"张三": "主角"},
            chapters=[Chapter(
                chapter_number=1,
                title="第一章",
                scenes=[Scene(
                    scene_number=1,
                    heading="内景 教室 - 白天",
                    location="教室",
                    time_of_day="白天",
                    int_ext="内景",
                    content=[Action(text="走进教室")],
                )],
            )],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = export_yaml(screenplay, Path(tmp), "test.yaml")
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "测试剧本" in content  # value 中文
            assert "title:" in content    # key 英文
            assert "走进教室" in content


# ═══════════════════════════════════════════════════════════════
# Pipeline 合并测试
# ═══════════════════════════════════════════════════════════════


CHUNK1_YAML = yaml.dump({
    "title": "测试", "genre": "武侠",
    "characters": {"张三": "主角"},
    "chapters": [{
        "chapter_number": 1, "title": "第一章",
        "scenes": [{
            "scene_number": 1, "heading": "内景 客栈 - 白天",
            "int_ext": "内景", "location": "客栈", "time_of_day": "白天",
            "content": [{"type": "action", "text": "走进客栈"}],
        }],
    }],
}, allow_unicode=True)

CHUNK2_YAML = yaml.dump({
    "characters": {"李四": "商人"},
    "chapters": [{
        "chapter_number": 1, "title": "第二章",
        "scenes": [{
            "scene_number": 1, "heading": "外景 街道 - 夜晚",
            "int_ext": "外景", "location": "街道", "time_of_day": "夜晚",
            "content": [{"type": "action", "text": "走在街上"}],
        }],
    }],
}, allow_unicode=True)


class TestPipelineMerge:
    def test_merge_results(self):
        """按顺序合并两个 chunk 的 YAML 结果。"""
        results = [(0, CHUNK1_YAML), (1, CHUNK2_YAML)]
        result = _merge_results(results, novel_name="测试")
        assert result.title == "测试"
        assert len(result.chapters) == 2
        assert result.chapters[0].chapter_number == 1
        assert result.chapters[1].chapter_number == 2
        assert "张三" in result.characters
        assert "李四" in result.characters

    def test_merge_results_out_of_order(self):
        """乱序结果 → 按索引排序后合并。"""
        results = [(1, CHUNK2_YAML), (0, CHUNK1_YAML)]
        result = _merge_results(results)
        assert result.chapters[0].chapter_number == 1

    def test_merge_empty_list(self):
        """空列表 → 抛出异常。"""
        with pytest.raises(ValueError):
            _merge_results([])


# ═══════════════════════════════════════════════════════════════
# API 测试
# ═══════════════════════════════════════════════════════════════


class TestAPI:
    def test_root(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["service"] == "novel2script"

    def test_sanitize_name_blocks_traversal(self):
        """路径遍历攻击被拦截。"""
        from app.api import _sanitize_name
        assert _sanitize_name("正常名字") == "正常名字"
        with pytest.raises(ValueError):
            _sanitize_name("../../etc/passwd")
        with pytest.raises(ValueError):
            _sanitize_name("../../../windows")
