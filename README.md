# novel2script

将中文网络小说自动转换为 LRM (Long-Running Movie) 脚本的工具。

## 特性

- 🔄 **多 Agent 架构** — 6 个专业 Agent 协作完成转换流水线
- 🎬 **LRM 脚本输出** — 结构化 YAML 格式，含镜头语言、对话、旁白
- 🤖 **MiLM 驱动** — 基于小米大模型（OpenAI 兼容接口）
- 🌐 **REST API** — FastAPI 提供 Web 服务接口
- ✅ **自动校验** — 输出结构完整性和一致性检查

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API 密钥
cp .env.example .env
# 编辑 .env，填入 MILM_API_KEY

# 3. 准备小说文件
mkdir -p novels/{小说名}/origin
# 将章节 .txt 文件放入 origin/ 目录

# 4. 运行转换
# 方式一：CLI
python -m app.main convert --novel-dir novels/{小说名}

# 方式二：API 服务
uvicorn app.main:app --reload
curl -X POST http://localhost:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"novel_dir": "novels/{小说名}"}'
```

## 项目结构

```
novel2script/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── api/routes.py        # REST API 路由
│   ├── agents/              # 多 Agent 流水线
│   │   ├── orchestrator.py  # 总调度器
│   │   ├── chapter_agent.py # 章节解析
│   │   ├── character_agent.py # 角色提取
│   │   ├── scene_agent.py   # 场景拆分
│   │   ├── dialogue_agent.py # 对话处理
│   │   ├── yaml_builder.py  # YAML 构建
│   │   └── validator_agent.py # 校验
│   ├── schema/              # Pydantic 数据模型
│   ├── parsers/             # 输入解析
│   ├── exporters/           # 输出导出
│   ├── prompts/             # 提示词模板
│   ├── services/            # LLM 服务、配置
│   └── utils/               # 工具函数
├── novels/                  # 小说输入
├── output/                  # 生成输出
├── tests/                   # 测试
└── frontend/                # 前端（预留）
```

## Agent 流水线

```
章节原文 → [chapter_agent] → 章节列表
         → [character_agent] → 角色图谱
         → [scene_agent] → 场景拆分 (×N章)
         → [dialogue_agent] → 镜头+对话 (×N场景)
         → [yaml_builder] → YAML 结构
         → [validator_agent] → 校验报告
         → [yaml_exporter] → script.yaml
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 健康检查 |
| GET | `/api/v1/health` | 服务状态 |
| GET | `/api/v1/novels` | 列出可用小说 |
| POST | `/api/v1/convert` | 触发转换任务 |

## 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `MILM_API_KEY` | ✅ | MiLM API 密钥 |
| `MILM_BASE_URL` | ❌ | API 端点（默认: https://api.xiaomi.com/v1） |
| `MILM_MODEL` | ❌ | 模型名称（默认: milm） |
| `TEMPERATURE` | ❌ | 生成温度（默认: 0.7） |
| `MAX_TOKENS` | ❌ | 最大 token（默认: 4096） |
| `OUTPUT_BASE` | ❌ | 输出目录（默认: output） |

## License

MIT
