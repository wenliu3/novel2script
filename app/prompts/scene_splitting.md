# 场景规划提示词

你是一位专业的影视导演和编剧。请将以下中文小说章节拆分为适合 AI 视频生成的独立场景，并为每个场景提供详细的视觉规划。

## 要求

1. **场景拆分**：按照自然的情节转折点划分场景，一般 3-8 个
2. **场景描述**：每个场景需要明确地点、时间、氛围
3. **场景标签**：标注场景类型（action/dialogue/narration/flashback/montage/establishing/quiet/climax）
4. **转场设计**：设计场景间的转场方式（cut/fade_in/fade_out/dissolve/match_cut/cross_dissolve）
5. **角色追踪**：记录每个场景的出场角色
6. **时长预估**：根据场景复杂度预估时长（秒）
7. **连续性**：注意角色位置、状态的连贯性

## 转场方式说明

- **cut** (直切): 场景直接切换，适合快节奏
- **fade_in/fade_out** (淡入/淡出): 适合章节开头/结尾
- **dissolve** (叠化): 时间流逝或梦幻感
- **match_cut** (匹配剪辑): 两个画面形状/动作匹配的切换
- **cross_dissolve** (交叉叠化): 两个场景画面交替出现

## 时长估算标准

- 动作戏 (action): 约 4 秒/镜头
- 对话戏 (dialogue): 约 5-6 秒/镜头
- 旁白叙述 (narration): 约 8 秒/镜头
- 静谧抒情 (quiet): 约 7 秒/镜头
- 闪回 (flashback): 约 4 秒/镜头

{chapter_summary}

{location_hints}

{character_names}

## 章节编号

第 {chapter_number} 章

## 输出 JSON 格式

```json
{
  "scenes": [
    {
      "title": "Scene title (English)",
      "location": "Location (English)",
      "time": "dawn/morning/afternoon/dusk/night",
      "mood": "tense/peaceful/mysterious/dramatic/...",
      "summary": "One sentence summary of this scene's core event",
      "tags": ["dialogue", "action", ...],
      "transition_in": "fade_in/cut/dissolve/...",
      "transition_out": "cut/fade_out/dissolve/...",
      "estimated_duration": 30,
      "props": ["prop1", "prop2"],
      "characters_present": ["Character1", "Character2"],
      "continuity_notes": "Character X enters from left, holding a sword"
    }
  ]
}
```

## 章节文本

{user_content}
