# PR-05：新增 Dialogue Writer Agent，实现小说叙述→对白+动作转换

## 功能描述

在场景拆分之后，将小说叙述文本转换为结构化剧本节拍和分镜头脚本：

- **动作节拍（action）**：从动作描写提炼简洁动作描述
- **对白节拍（dialogue）**：直接引语保留 + 间接叙述展开为具体对白 + 暗示互动推断对白
- **旁白节拍（narration）**：环境氛围、内心独白等
- **分镜头（shots）**：可选，含机位、景别、画面描述、镜头运动

### 使用方式

```python
agent = DialogueAgent(llm)

# 完整调用（节拍 + 镜头）
scene = agent.execute(scene, chapter_text, chapter_number=1, character_names=["张三"])

# 仅节拍
beats = agent.generate_beats(scene, chapter_text, character_names=["张三"])

print(scene.action_beats)    # 所有动作节拍
print(scene.dialogue_beats)  # 所有对白节拍
```

## 实现思路

1. **Beat 模型**：新增 `type`/`character`/`content` 三字段最小叙事单元，融入 Scene 模型，提供 `action_beats`/`dialogue_beats` 过滤属性
2. **LLM Prompt**：三类型节拍转换规则（直接引语→保留 / 间接叙述→展开 / 动作→提炼），强制 JSON 输出
3. **错误隔离**：LLM 失败返回原 Scene（空 beats），不阻断流水线
4. **向后兼容**：`execute()` 签名不变，beat 解析失败不影响 shot 生成

## 测试方式

```bash
pytest tests/test_agents/test_dialogue_agent.py -v   # 10 tests passed
```

| 维度 | 用例 | 覆盖 |
|---|---|---|
| Beat 模型 | 4 | action/dialogue/narration 创建与序列化 |
| Scene.beats | 2 | action_beats/dialogue_beats 过滤、空列表 |
| DialogueAgent | 4 | 节拍生成、便捷方法、LLM 异常降级、镜头生成 |
