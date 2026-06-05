# 章节提取提示词

请分析以下中文小说章节文本，完成以下任务：

1. 提取章节标题
2. 识别所有出现的人物
3. 总结章节主要事件

## 输出 JSON 格式

```json
{
  "chapter_title": "章节标题",
  "characters_seen": ["角色1", "角色2"],
  "summary": "章节摘要"
}
```

## 章节文本

{user_content}
