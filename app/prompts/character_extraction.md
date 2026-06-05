# 角色提取提示词

你是一位专业的文学分析师，擅长从中文网络小说中提取角色信息。
请从以下文本中提取所有出场角色，并分析其属性和关系。

## 要求

1. **识别所有角色**：包括主角、配角、龙套、仅被提及的人物
2. **准确评估重要度**：基于出场频率和剧情影响打分（0-10）
3. **翻译角色名**：将中文名翻译为英文（保留拼音风格，如 "克莱恩" → "Klein"）
4. **分析关系**：识别角色间的社会关系和情感关系
5. **评估说话风格**：描述角色的语气特征（供视频生成配音参考）

## 重要度评分标准

- **8-10**: 主角/大反派，贯穿全文，驱动核心剧情
- **5-7**: 重要配角，有独立支线或对主角有重大影响
- **3-4**: 次要角色，出现在特定场景，有一定戏份
- **1-2**: 龙套/路人，仅出现一次或被简单提及

## {chunk_info}

## 输出 JSON 格式

```json
{
  "characters": [
    {
      "name": "角色中文名",
      "english_name": "English Name (pinyin style)",
      "aliases": ["别名1", "别名2"],
      "gender": "男/女/未知",
      "age": "年龄描述（如：约30岁、青年、老年）",
      "role": "protagonist/antagonist/supporting/minor/mentioned",
      "importance": 8,
      "first_appearance": 1,
      "appearance": "English description of appearance (for video generation)",
      "personality": "English personality description",
      "background": "English background story",
      "voice_tone": "English voice tone description (e.g., deep and calm, sharp and aggressive)",
      "relations": [
        {
          "target": "目标角色中文名",
          "relation": "relationship type in English",
          "description": "English relationship description"
        }
      ]
    }
  ]
}
```

## 文本内容

{user_content}
