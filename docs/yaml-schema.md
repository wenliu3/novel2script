# LRM 剧本 YAML Schema 定义

> novel2script 输出的 YAML 剧本格式。英文 key + 中文 value。

## 设计原则

1. **英文 key + 中文 value**：key 用英文（title、chapters、scenes），value 用中文（角色名、对白、地点）
2. **扁平 content 列表**：`content` 是 Action 和 DialogueLine 的有序列表
3. **嵌套不超过 4 层**：Screenplay → Chapter → Scene → Content Item
4. **角色用中文名**：不用 ID，直接 `characters: {"叶凡": "主角"}`
5. **宽松兼容**：所有字段有默认值，容忍 LLM 输出格式偏差

## 完整 Schema

```yaml
title: 遮天
author: 辰东
genre: 仙侠
characters:
  叶凡: "主角，大学生"
  庞博: "叶凡的好友"

chapters:
  - chapter_number: 1
    title: "第001章 星空中的青铜巨棺"
    scenes:
      - scene_number: 1
        heading: "外景 宇宙深处 - 夜晚"
        int_ext: "外景"
        location: "宇宙深处"
        time_of_day: "夜晚"
        characters:
          - "宇航员"
        summary: "旅行者二号发现九具龙尸"
        content:
          - type: action
            text: "冰冷与黑暗并存的宇宙深处，九具庞大的龙尸拉着一口青铜古棺。"
          - type: dialogue
            character: "宇航员"
            text: "上帝，我看到了什么？"

      - scene_number: 2
        heading: "内景 叶凡宿舍 - 白天"
        int_ext: "内景"
        location: "叶凡宿舍"
        time_of_day: "白天"
        characters:
          - "叶凡"
        summary: "叶凡翻看黄帝内经"
        content:
          - type: action
            text: "叶凡合上黄帝内经，准备出门参加同学聚会。"
```

## 字段说明

### 顶层（Screenplay）

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 小说名（来自前端输入） |
| `author` | string | 原著作者 |
| `genre` | string | 类型（仙侠/武侠/都市等） |
| `characters` | map | 角色名 → 简介 |
| `chapters` | array | 章节列表 |

### 章节（Chapter）

| 字段 | 类型 | 说明 |
|------|------|------|
| `chapter_number` | int | 全局连续编号 |
| `title` | string | 章节标题（保留原文章节名） |
| `scenes` | array | 场景列表 |

### 场景（Scene）

| 字段 | 类型 | 说明 |
|------|------|------|
| `scene_number` | int | 章节内序号 |
| `heading` | string | "内景/外景 地点 - 时间" |
| `int_ext` | string | "内景" 或 "外景" |
| `location` | string | 地点 |
| `time_of_day` | string | 时间（白天/夜晚/黄昏等） |
| `characters` | array | 出场角色名 |
| `summary` | string | 一句话概括 |
| `content` | array | Action/DialogueLine 交替列表 |

### 动作（Action）

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | "action" | 类型标签 |
| `text` | string | 动作描述 |

### 对白（DialogueLine）

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | "dialogue" | 类型标签 |
| `character` | string | 说话角色名 |
| `text` | string | 对白内容 |
| `parenthetical` | string | 表演提示（可选） |

## 容错机制

LLM 输出的 YAML 可能有格式偏差，系统自动修复：

| 问题 | 修复方式 |
|------|---------|
| Scene 用 `title` 代替 `heading` | 自动映射 |
| 缺少 `int_ext`/`location`/`time_of_day` | 默认空字符串 |
| 内容放在 `description` 而非 `content` | 自动转为 content |
| Tab 缩进 | 自动转为空格 |
| 中文冒号 `：` | 自动转为英文 `: ` |
| markdown 代码块包裹 | 自动去除 |
