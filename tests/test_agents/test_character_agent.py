"""人物分析 Agent 测试。

测试角色模型、合并逻辑、重要度推断等核心功能。
注意：LLM 相关的测试需要真实 API 连接，标记为 slow 跳过。
"""

import pytest
from app.schema.character import (
    Character,
    CharacterList,
    CharacterRelation,
    CharacterRole,
    _merge_characters,
)
from app.agents.character_agent import CharacterAgent, _infer_role


# ──────────────────────────────────────
# 角色数据模型测试
# ──────────────────────────────────────


class TestCharacterModel:
    """角色模型基础测试。"""

    def test_create_character(self):
        """创建角色对象。"""
        c = Character(name="张三", importance=8, role=CharacterRole.PROTAGONIST)
        assert c.name == "张三"
        assert c.importance == 8
        assert c.role == CharacterRole.PROTAGONIST

    def test_character_defaults(self):
        """默认值应正确。"""
        c = Character(name="路人甲")
        assert c.importance == 0
        assert c.role == CharacterRole.MINOR
        assert c.aliases == []
        assert c.relations == []


class TestCharacterList:
    """角色列表测试。"""

    def test_find_by_name(self):
        cl = CharacterList(characters=[
            Character(name="张三", english_name="Zhang San"),
            Character(name="李四", aliases=["四哥"]),
        ])
        assert cl.find_by_name("张三").english_name == "Zhang San"
        assert cl.find_by_name("四哥").name == "李四"
        assert cl.find_by_name("不存在") is None

    def test_find_by_english_name(self):
        cl = CharacterList(characters=[
            Character(name="克莱恩", english_name="Klein"),
        ])
        assert cl.find_by_english_name("klein").name == "克莱恩"

    def test_get_main_characters(self):
        cl = CharacterList(characters=[
            Character(name="主角", importance=9),
            Character(name="配角", importance=5),
            Character(name="龙套", importance=1),
        ])
        main = cl.get_main_characters(min_importance=5)
        assert len(main) == 2
        assert main[0].name == "主角"

    def test_to_markdown(self):
        cl = CharacterList(characters=[
            Character(
                name="克莱恩",
                english_name="Klein",
                role=CharacterRole.PROTAGONIST,
                importance=9,
                personality="Calm and analytical",
            ),
        ])
        md = cl.to_markdown()
        assert "克莱恩" in md
        assert "Klein" in md
        assert "protagonist" in md


class TestCharacterMerge:
    """角色合并测试。"""

    def test_merge_same_name(self):
        """同名角色应合并信息。"""
        a = CharacterList(characters=[
            Character(name="张三", importance=5, gender="男", aliases=["三哥"]),
        ])
        b = CharacterList(characters=[
            Character(name="张三", importance=8, personality="Brave"),
        ])
        merged = a.merge(b)
        assert len(merged.characters) == 1
        assert merged.characters[0].importance == 8  # 取最高
        assert merged.characters[0].gender == "男"   # 保留旧值
        assert merged.characters[0].personality == "Brave"  # 补充新值
        assert "三哥" in merged.characters[0].aliases

    def test_merge_new_characters(self):
        """新角色应被添加。"""
        a = CharacterList(characters=[
            Character(name="张三", importance=5),
        ])
        b = CharacterList(characters=[
            Character(name="李四", importance=3),
        ])
        merged = a.merge(b)
        assert len(merged.characters) == 2

    def test_merge_relations(self):
        """关系应去重合并。"""
        a = CharacterList(characters=[
            Character(name="张三", relations=[
                CharacterRelation(target="李四", relation="friend"),
            ]),
        ])
        b = CharacterList(characters=[
            Character(name="张三", relations=[
                CharacterRelation(target="李四", relation="rival"),
                CharacterRelation(target="王五", relation="brother"),
            ]),
        ])
        merged = a.merge(b)
        relations = merged.characters[0].relations
        targets = [r.target for r in relations]
        assert "李四" in targets
        assert "王五" in targets
        assert len(relations) == 2  # 李四去重，王五新增

    def test_merge_sorted_by_importance(self):
        """合并后应按重要度降序排列。"""
        a = CharacterList(characters=[
            Character(name="A", importance=3),
        ])
        b = CharacterList(characters=[
            Character(name="B", importance=9),
        ])
        merged = a.merge(b)
        assert merged.characters[0].name == "B"
        assert merged.characters[1].name == "A"


# ──────────────────────────────────────
# 角色定位推断
# ──────────────────────────────────────


class TestRoleInference:
    """重要度→角色定位推断测试。"""

    def test_protagonist(self):
        assert _infer_role(9) == CharacterRole.PROTAGONIST

    def test_supporting(self):
        assert _infer_role(6) == CharacterRole.SUPPORTING

    def test_minor(self):
        assert _infer_role(4) == CharacterRole.MINOR

    def test_mentioned(self):
        assert _infer_role(1) == CharacterRole.MENTIONED


# ──────────────────────────────────────
# CharacterAgent 文本切分测试
# ──────────────────────────────────────


class TestCharacterAgentChunking:
    """Agent 文本切分逻辑测试（不需要 LLM 连接）。"""

    def test_short_text_no_split(self):
        """短文本不应被切分。"""
        agent = CharacterAgent.__new__(CharacterAgent)
        agent.chunk_size = 8000
        text = "这是一段短文本。"
        chunks = agent._split_into_chunks(text)
        assert len(chunks) == 1

    def test_long_text_split_by_chapter(self):
        """长文本应按章节分隔符切分。"""
        agent = CharacterAgent.__new__(CharacterAgent)
        agent.chunk_size = 100
        text = "=== 第1章 ===\n" + "内容" * 60 + "\n=== 第2章 ===\n" + "内容" * 60
        chunks = agent._split_into_chunks(text)
        assert len(chunks) >= 2

    def test_very_long_paragraph_split(self):
        """超长段落应按句子切分。"""
        agent = CharacterAgent.__new__(CharacterAgent)
        agent.chunk_size = 100
        # 没有章节分隔符的长文本
        text = "这是很长的内容。" * 50
        chunks = agent._split_into_chunks(text)
        for chunk in chunks:
            assert len(chunk) <= 150  # 允许少量超出（句子边界）


# ──────────────────────────────────────
# LLM 集成测试（需要 API 连接，默认跳过）
# ──────────────────────────────────────


@pytest.mark.slow
class TestCharacterAgentLLM:
    """需要真实 LLM 连接的测试。标记 @pytest.mark.slow，默认跳过。"""

    def test_extract_characters(self):
        """从文本中提取角色。"""
        from app.services.config import load_settings
        from app.services.llm_service import LLMService

        try:
            settings = load_settings()
        except ValueError:
            pytest.skip("未配置 MILM_API_KEY，跳过 LLM 测试")

        llm = LLMService(settings)
        agent = CharacterAgent(llm)

        text = """第一章 相遇

张三是一个年轻的剑客，性格刚毅。他在山路上遇到了李四，一个神秘的老人。

"你叫什么名字？"张三问道。
"我叫李四，你可以叫我四哥。"老人微笑着说。"""

        result = agent.execute(chapters_text=text)
        assert len(result.characters) >= 1
        names = [c.name for c in result.characters]
        assert any("张" in n or "李" in n for n in names)
