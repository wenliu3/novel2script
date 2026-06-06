# PR-07 + PR-08：YAML Builder + Validator Agent

## 功能描述

**PR-07 YAML Builder**：将所有上游 Agent 输出组装为完整 Script，生成角色 ID 映射并规范化 beat 引用。

**PR-08 Validator**：多维校验 + 7 项自动修复（空 ID、缺字段、非法类型等）。

### 使用方式

```python
# YAML Builder
script = YAMLBuilderAgent(llm).execute(
    novel_name="诡夜客栈",
    chapter_scripts=[(1, "第一章", scenes)],
    characters=char_list,
    chapter_report=analysis_report,
    genre="悬疑",
)
# → Script(title/genre/logline/source/characters/chapters/metadata)

# Validator
result = ValidatorAgent(llm).execute(script)
# → result.is_valid / errors / warnings / fixes_applied
```

## 实现思路

1. **Script Schema 增强**：新增 `ScriptCharacter`（id/name/role）、`genre`、`logline`、`source` 字段
2. **角色 ID 映射**：按 importance 降序分配 `char_001` 格式 ID，别名映射到同一 ID，beat 中角色名替换为 ID
3. **分层校验**：结构层 → 角色层 → beat/shot 层 → LLM 可选内容检查
4. **自动修复**：空 ID 自动生成、空 type→action、dialogue 缺角色→未知、空 genre→未分类

## 测试方式

```bash
pytest tests/test_agents/test_yaml_builder.py -v    # 8 tests
pytest tests/test_agents/test_validator_agent.py -v  # 17 tests
```

| 模块 | 用例 | 覆盖 |
|---|---|---|
| YAML Builder | 8 | 组装、角色 ID 映射、beat 规范化、metadata 统计 |
| Validator | 17 | 结构/beat/角色引用校验、7 项自动修复、异常降级 |
