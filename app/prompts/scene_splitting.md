# 场景拆分提示词

你是一位专业的影视编剧。请将以下中文小说章节拆分为适合 AI 视频生成的独立场景。

## 要求

1. 按照自然的情节转折点划分场景
2. 每个场景需要明确：地点、时间、氛围
3. 列出场景中的关键道具
4. 一般一个章节拆分为 3-8 个场景

## 输出 JSON 格式

```json
{
  "scenes": [
    {
      "title": "场景标题（英文）",
      "location": "地点（英文）",
      "time": "时间：dawn/morning/afternoon/dusk/night",
      "mood": "氛围（英文，如 tense, peaceful, mysterious）",
      "props": ["关键道具1", "关键道具2"]
    }
  ]
}
```

## 章节编号

第 {chapter_number} 章

{character_names}

## 章节文本

{user_content}
