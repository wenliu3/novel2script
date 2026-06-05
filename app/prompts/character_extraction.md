# 角色提取提示词

你是一位专业的文学分析师。请从以下中文小说文本中提取所有角色信息。

## 要求

1. 识别所有出场角色（包括只被提及的角色）
2. 提取每个角色的关键属性
3. 分析角色之间的关系
4. 将角色名翻译为英文（保留中文原名在括号中）
5. 如果已有角色列表，补充新角色并更新已有信息

## 输出 JSON 格式

```json
{
  "characters": [
    {
      "name": "角色中文名",
      "english_name": "English Name",
      "aliases": ["别名1"],
      "gender": "男/女/未知",
      "age": "年龄描述",
      "appearance": "外貌特征（英文）",
      "personality": "性格描述（英文）",
      "background": "背景故事（英文）",
      "relations": [
        {
          "target": "目标角色名",
          "relation": "关系类型",
          "description": "关系描述（英文）"
        }
      ]
    }
  ]
}
```

## 文本内容

{user_content}
