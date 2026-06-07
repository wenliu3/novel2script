# LRM 剧本 YAML Schema 定义

novel2script 输出的剧本格式规范。本文档分两部分：第一部分说明各项设计决策的原因，第二部分给出完整的字段参考。

---

## 一、设计原因

### 1. 为什么选择 YAML，而不是 JSON 或 XML

剧本的核心内容是对白和动作描述，都是自然语言文本。YAML 对长字符串的支持比 JSON 更友好——块标量（`|`）可以保留换行，不需要转义引号，作者直接打开文件就能阅读和编辑，不会被大量的 `"` 和 `\n` 干扰。

JSON 的优势在于机器解析，但这个工具的目标用户是作者，最终产物需要人工打磨，可读性比解析性能更重要。XML 则过于冗长，不适合频繁手工编辑的场景。

### 2. 为什么用英文 key + 中文 value

剧本文件需要被下游工具链（渲染器、导入插件、版本控制差异对比）处理。英文 key 保证了与工具链的兼容性——绝大多数 YAML 解析库对英文 key 的支持没有任何边界情况。

中文 value 是因为内容本身是中文创作，角色名、地点、对白如果转成拼音或英文会丢失信息，也不方便作者核对。两者分开，各司其职。

### 3. 为什么把对白和动作放在同一个 `content` 列表里

剧本的叙事是线性的：一段动作描述之后紧跟一句对白，对白之后可能又是动作。如果把动作和对白分成两个独立列表，就丢失了它们之间的顺序关系。

```yaml
# ❌ 分开存储：无法表达"先动作后对白"的时序
actions:
  - 张三推开门
dialogues:
  - character: 张三
    text: 有人吗？

# ✅ 统一列表：顺序即叙事顺序
content:
  - type: action
    text: 张三推开门
  - type: dialogue
    character: 张三
    text: 有人吗？
```

每个条目用 `type` 字段区分类型，解析时按 `type` 分发，不影响程序处理。

### 4. 为什么 `content` 条目用 `type` 字段而不是用不同的 key 名区分

另一种常见设计是用不同的顶层 key 来区分类型：

```yaml
# 替代方案：用 key 名区分
- action: 张三推开门
- dialogue:
    character: 张三
    text: 有人吗？
```

这种方式解析时需要对每个条目做 key 枚举才能判断类型，扩展新类型（比如未来加入`旁白`、`字幕`）也需要修改解析逻辑。`type` 字段是标准的判别联合（discriminated union）模式，扩展性更好，LLM 生成时也更不容易出错。

### 5. 为什么嵌套不超过 4 层

```
Screenplay → chapters → scenes → content
    1              2        3        4
```

超过 4 层的 YAML 在手工编辑时极易出现缩进错误，作者需要反复数空格来确认层级。4 层已经足以表达"剧本 → 章节 → 场景 → 内容"的完整结构，没有必要再深。

### 6. 为什么 `characters` 用映射（map）而不是对象列表

```yaml
# 对象列表方案
characters:
  - name: 叶凡
    description: 主角，大学生

# 本方案：映射
characters:
  叶凡: 主角，大学生
```

剧本里角色名是天然的唯一标识符。用映射可以直接通过角色名查找描述，不需要遍历列表。作者添加或修改角色时也更直观，直接改对应的行即可。

顶层 `characters` 的定位是"角色备忘录"，供作者和后续工具快速查阅，不是详细的角色档案。详细的角色信息（性格、外貌、关系）属于另一层文档，不应该塞进剧本文件。

### 7. 为什么 `chapter_number` 保留原著编号，不重新从 1 连续编排

小说原著的章节编号有实际意义——作者对章节的认知是"第 87 章出了问题"，而不是"第 12 个处理块出了问题"。如果系统重新编号，作者在原著和剧本之间对照时会产生混乱。

保留原始编号也意味着编号可以不连续（比如只转换了部分章节），这对增量处理和局部重跑都有好处。

### 8. 为什么 `heading` 采用"内景/外景 地点 - 时间"的固定格式

这是好莱坞剧本的标准场景标题格式（Scene Heading / Slugline），被 Final Draft、Fountain 等主流剧本工具广泛支持。固定格式意味着可以被程序可靠地解析，同时作者也能直接看懂。

```
INT. COFFEE SHOP - DAY        ← 英文格式
内景 咖啡厅 - 白天             ← 中文等价
```

`int_ext`、`location`、`time_of_day` 三个字段是对 `heading` 的结构化拆解，方便按地点或时间段过滤场景，不需要再对 `heading` 做字符串解析。

### 9. 为什么所有字段都有默认值（宽松 Schema）

本工具的输出来自 LLM，LLM 不可避免地会漏填字段、用错字段名。如果 Schema 是严格的（缺少字段就报错），那么一个章节的格式错误会导致整本书的转换失败。

宽松 Schema 的策略是：能解析的尽量解析，不能解析的字段用空值或空列表填充，保证作者拿到的永远是一个完整的文件，最差情况也只是某些字段为空，而不是文件损坏。

---

## 二、完整字段参考

### 顶层（Screenplay）

```yaml
title: 遮天                          # 剧本标题（来自小说名称）
author: 辰东                          # 原著作者（可选）
genre: 仙侠                           # 类型：仙侠/武侠/都市/奇幻 等（可选）
characters:                           # 角色备忘录
  叶凡: 主角，大学生
  庞博: 叶凡的好友
chapters:                             # 章节列表（见下）
  - ...
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 剧本标题，默认"未命名剧本" |
| `author` | string | ❌ | 原著作者 |
| `genre` | string | ❌ | 类型标签 |
| `characters` | map\<string, string\> | ❌ | 角色名 → 简介，供快速查阅 |
| `chapters` | array | ✅ | 章节列表，可为空数组 |

---

### 章节（Chapter）

```yaml
chapters:
  - chapter_number: 87               # 原著章节编号（保留原始值）
    title: 九龙拉棺                   # 章节简短标题
    chapter_title: 第087章 九龙拉棺   # 原著完整章节名（含"第X章"前缀）
    scenes:
      - ...
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `chapter_number` | int | ✅ | 原著章节编号，不重新排序 |
| `title` | string | ❌ | 章节简短标题 |
| `chapter_title` | string | ❌ | 原著完整章节名 |
| `scenes` | array | ✅ | 场景列表，可为空数组 |

---

### 场景（Scene）

```yaml
scenes:
  - scene_number: 1                  # 章节内序号，从 1 开始
    heading: "外景 宇宙深处 - 夜晚"   # 场景标题，格式：内景/外景 地点 - 时间
    int_ext: 外景                     # 内景 或 外景
    location: 宇宙深处                # 地点名称
    time_of_day: 夜晚                 # 白天 / 夜晚 / 黄昏 / 清晨 等
    characters:                       # 本场景出场角色
      - 宇航员
    summary: 旅行者二号发现九具龙尸    # 一句话概括（可选）
    content:                          # 动作和对白的有序列表（见下）
      - ...
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `scene_number` | int | ✅ | 章节内序号 |
| `heading` | string | ✅ | 场景标题，遵循"内景/外景 地点 - 时间"格式 |
| `int_ext` | string | ❌ | `内景` 或 `外景`，`heading` 的结构化拆解 |
| `location` | string | ❌ | 地点，`heading` 的结构化拆解 |
| `time_of_day` | string | ❌ | 时间段，`heading` 的结构化拆解 |
| `characters` | array\<string\> | ❌ | 出场角色名列表 |
| `summary` | string | ❌ | 场景一句话概括 |
| `content` | array | ✅ | 动作与对白的有序列表，可为空数组 |

---

### 动作条目（Action）

```yaml
content:
  - type: action
    text: 冰冷与黑暗并存的宇宙深处，九具庞大的龙尸拉着一口青铜古棺缓缓漂移。
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"action"` | ✅ | 固定值，用于区分条目类型 |
| `text` | string | ✅ | 动作或场景描述，可多句 |

---

### 对白条目（DialogueLine）

```yaml
content:
  - type: dialogue
    character: 宇航员
    text: 上帝，我看到了什么？
    parenthetical: 颤抖着          # 表演提示，可选
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"dialogue"` | ✅ | 固定值，用于区分条目类型 |
| `character` | string | ✅ | 说话的角色名，与顶层 `characters` 对应 |
| `text` | string | ✅ | 对白内容 |
| `parenthetical` | string | ❌ | 括号内的表演提示，如"低声"、"激动地" |

---

## 三、完整示例

```yaml
title: 遮天
author: 辰东
genre: 仙侠
characters:
  叶凡: 主角，北京大学在读学生
  庞博: 叶凡的室友

chapters:
  - chapter_number: 1
    title: 星空中的青铜巨棺
    chapter_title: 第001章 星空中的青铜巨棺
    scenes:
      - scene_number: 1
        heading: 外景 宇宙深处 - 夜晚
        int_ext: 外景
        location: 宇宙深处
        time_of_day: 夜晚
        characters:
          - 旁白
        summary: 旅行者二号在太阳系边缘发现异象
        content:
          - type: action
            text: 冰冷与黑暗并存的宇宙深处，九具庞大的龙尸拉着一口青铜古棺缓缓漂移。

      - scene_number: 2
        heading: 内景 叶凡宿舍 - 清晨
        int_ext: 内景
        location: 北京大学宿舍
        time_of_day: 清晨
        characters:
          - 叶凡
          - 庞博
        summary: 叶凡告别室友，独自前往泰山
        content:
          - type: action
            text: 叶凡收拾好背包，庞博靠在床头刷手机。
          - type: dialogue
            character: 庞博
            text: 你一个人去泰山？不等我们？
          - type: dialogue
            character: 叶凡
            text: 我想一个人静静。
            parenthetical: 背对着庞博
          - type: action
            text: 叶凡拎起背包，头也不回地走出宿舍。
```

---

## 四、容错规则

LLM 生成的 YAML 可能存在格式偏差，系统会自动尝试修复以下问题，修复失败时对应字段置为空值，不中断整体转换流程。

| 问题 | 修复方式 |
|------|---------|
| `scene.title` 代替 `scene.heading` | 自动将 `title` 的值映射到 `heading` |
| `description` / `text` 代替 `content` | 转为单条 `action` 类型的 `content` 条目 |
| 缺少 `int_ext` / `location` / `time_of_day` | 填入空字符串 |
| Tab 缩进 | 替换为两个空格 |
| 中文冒号 `：` | 替换为英文冒号加空格 `: ` |
| Markdown 代码块包裹（` ```yaml `） | 自动去除 |
| YAML 语法错误 | 触发一次 LLM 重新生成，仍失败则跳过该章节 |