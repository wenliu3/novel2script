# novel2script

中文网络小说 → LRM (Long-Running Movie) 剧本 YAML 的自动转换系统。

输入一篇 TXT 小说，自动按章节切分 → 多线程并行调用 LLM → 输出结构化 YAML 剧本。

## 架构

```
TXT 小说
  │
  ▼
Splitter（正则切分章节）         纯 Python
  │  按 "第X章" 等标记切分
  ▼
Pipeline ─────────────────────  并行处理
  │  章节1 → agent(LLM) → YAML₁  ─┐
  │  章节2 → agent(LLM) → YAML₂  ─┤  同时进行
  │  章节3 → agent(LLM) → YAML₃  ─┤
  │  ...                           │
  ▼                                │
合并（按章节顺序）──────────────────┘
  │  角色去重 + 章节重编号
  ▼
Builder（YAML 导出）             纯 Python
  ▼
YAML 剧本文件
```

**每章独立处理，互不依赖，多线程并行加速。**

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API 密钥
cp .env.example .env
# 编辑 .env，填入你的 LLM API 密钥

# 3. 启动后端
uvicorn app.main:app --reload

# 4. 启动前端（另开终端）
cd frontend && npm install && npm run dev
```

- 后端 API 文档: http://localhost:8000/docs
- 前端界面: http://localhost:3000

## 使用流程

1. 打开前端界面 http://localhost:3000
2. 输入小说名称，选择 TXT 文件上传
3. 点击「开始转换」
4. 等待处理完成（进度实时更新）
5. 下载生成的 YAML 剧本文件

## 项目结构

```
app/
├── main.py           # FastAPI 入口
├── config.py         # 配置 + 日志
├── llm.py            # LLM 服务（OpenAI 兼容，自动重试）
├── models.py         # 数据模型（宽松 Schema，容忍 LLM 输出偏差）
├── api.py            # API 端点
└── core/
    ├── agent.py      # ScriptAgent — 调用 LLM，输出 YAML
    ├── builder.py    # YAML 导出
    ├── pipeline.py   # 主流水线（并行处理 + 合并）
    └── splitter.py   # 文本切分 + 编码检测 + 章节识别

frontend/src/
├── App.vue           # 单页应用（上传 → 转换 → 下载）
├── main.js
└── api/index.js
```

## 输出示例

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
        characters: ["宇航员"]
        content:
          - type: action
            text: "冰冷与黑暗并存的宇宙深处，九具龙尸拉着一口青铜古棺。"
          - type: dialogue
            character: "宇航员"
            text: "上帝，我看到了什么？"
```

完整 Schema 见 [docs/yaml-schema.md](docs/yaml-schema.md)。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 健康检查 |
| POST | `/api/upload` | 上传小说文件（TXT） |
| POST | `/api/convert` | 触发转换（后台并行运行） |
| GET | `/api/status/{task_id}` | 查询任务状态 + 进度 |
| GET | `/api/download/{name}` | 下载 YAML 文件 |

## 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `MILM_API_KEY` | ✅ | — | LLM API 密钥 |
| `MILM_BASE_URL` | ❌ | `https://token-plan-cn.xiaomimimo.com/v1` | API 端点（OpenAI 兼容） |
| `MILM_MODEL` | ❌ | `mimo-v2.5` | 模型名称 |
| `TEMPERATURE` | ❌ | `0.7` | 生成温度 |
| `MAX_TOKENS` | ❌ | `16000` | 单次最大输出 token |
| `CHUNK_SIZE` | ❌ | `100000` | 每块大小（字符数） |

## 测试

```bash
pytest tests/ -v
```

## 技术栈

| 组件 | 技术 |
|------|------|
| LLM | OpenAI 兼容接口（小米 MiMo / GPT / DeepSeek 等） |
| 后端 | Python 3.11+ / FastAPI / Uvicorn |
| 数据模型 | Pydantic v2（宽松 Schema） |
| 并行处理 | ThreadPoolExecutor |
| 文本切分 | 正则章节检测 + 递归字符切分 |
| 前端 | Vue 3 + Vite + Axios |

## License

MIT
