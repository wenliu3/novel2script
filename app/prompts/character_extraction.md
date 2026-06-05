# 角色提取与分析提示词

<<<<<<< HEAD
你是一位专业的文学分析师，擅长从中文网络小说中提取角色信息。
请从以下文本中提取所有出场角色，并分析其属性和关系。
=======
你是一位专业的文学分析师，擅长从中文小说文本中提取角色信息并分析角色关系。
请从以下小说章节文本中提取所有角色信息，并分析角色之间的关系。
>>>>>>> main

## 提取要求

<<<<<<< HEAD
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
=======
### 1. 角色识别
- 识别本章所有出场角色（包括对话中提及但未直接出场的人物）
- 注意角色的别名、绰号、尊称等，全部记录到 aliases 列表
- 区分同一角色的不同称呼（如"张先生""老张""张老师"都是同一个人）

### 2. 角色属性提取
- **name**: 角色正式中文名
- **english_name**: 英文名/拼音音译，如 "Zhang Wei"
- **aliases**: 别名列表，如 ["老张", "张先生", "师父"]
- **gender**: 男 / 女 / 未知
- **age**: 年龄描述，如 "约25岁"、"中年"、"老年"
- **appearance**: 外貌特征，用英文描述，如 "Tall, with sharp eyes and a commanding presence"
- **personality**: 性格描述，用英文描述，如 "Brave but impulsive, loyal to friends"
- **background**: 背景故事，用英文描述，如 "A former soldier who retired after a tragic mission"
- **role_type**: 角色定位，可选值：
  - "主角" - 故事的核心人物，有大量戏份和完整故事弧
  - "重要配角" - 戏份较多，对主线有重要影响的角色
  - "配角" - 有固定出场但戏份较少的角色
  - "龙套" - 仅在特定场景短暂出现的角色
- **importance_score**: 重要性评分（0.0-1.0），基于出场频率、对话量、对情节的影响度综合评估

### 3. 关系分析
分析本章中出现的角色关系，每条关系包含：
- **target**: 关系目标角色名
- **relation**: 关系类型，如：师徒、兄弟、父子、母女、恋人、朋友、敌人、上下级、同门、同学、邻居、合作伙伴、竞争对手、暗恋、救命恩人
- **description**: 关系描述，用英文，如 "Master and apprentice, trained together for 10 years"
- **strength**: 关系强度（1-10），基于亲密程度、互动频率、情感深度评估
- **direction**: 关系方向：
  - "双向" - 双方对彼此有相同的情感/关系（如互相爱慕的恋人）
  - "A→B" - A 对 B 单方面（如 A 暗恋 B）
- **change_over_time**: 关系随时间的变化描述，如 "从敌对到互相欣赏"、"一直亲密无间"

### 4. 本章出场信息
- 列出本章所有出场角色
- 识别本章的视角角色/核心角色
- 标记本章首次出场的新角色
- 分析本章的关键关系变化
>>>>>>> main

## 输出 JSON 格式

```json
{
  "chapter_characters": {
    "chapter_number": 1,
    "main_character": "视角角色名",
    "characters": ["角色名1", "角色名2"],
    "new_characters": ["本章新出现的角色名"],
    "key_relations": [
      {
        "source": "角色A",
        "target": "角色B",
        "change": "关系变化描述"
      }
    ]
  },
  "characters": [
    {
      "name": "角色中文名",
<<<<<<< HEAD
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
=======
      "english_name": "English Name",
      "aliases": ["别名1", "别名2"],
      "gender": "男/女/未知",
      "age": "年龄描述",
      "appearance": "外貌特征（英文）",
      "personality": "性格描述（英文）",
      "background": "背景故事（英文）",
      "role_type": "主角/重要配角/配角/龙套",
      "importance_score": 0.85,
      "relations": [
        {
          "target": "目标角色名",
          "relation": "关系类型",
          "description": "关系描述（英文）",
          "strength": 8,
          "direction": "双向/A→B",
          "change_over_time": "关系变化描述"
>>>>>>> main
        }
      ]
    }
  ]
}
```

## 处理说明
1. 如果已有角色列表提供，请更新已有角色的信息（新增别名、补充关系等），不要重复添加
2. 新发现的角色添加到列表中
3. 关系分析应基于本章的互动内容，避免过度推断

## 文本内容

{user_content}
