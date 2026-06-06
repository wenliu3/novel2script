# novel2script Web 前端设计文档

## 技术栈

- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **HTTP 客户端**: Axios
- **路由**: Vue Router 4
- **UI 组件**: 自定义轻量组件（不引入重量级 UI 库）

## 目录结构

```
frontend/
├── index.html                 # 入口 HTML
├── package.json               # 依赖配置
├── vite.config.js             # Vite 配置（代理后端 API）
├── src/
│   ├── main.js                # Vue 入口
│   ├── App.vue                # 根组件（布局 + 路由视图）
│   ├── router/
│   │   └── index.js           # 路由定义
│   ├── api/
│   │   └── index.js           # Axios 实例 + API 函数
│   ├── views/
│   │   ├── Home.vue           # 首页：小说列表 + 上传
│   │   ├── NovelDetail.vue    # 小说详情：章节管理 + 发起转换
│   │   └── Result.vue         # 结果页：YAML 预览 + 下载
│   ├── components/
│   │   ├── NovelCard.vue      # 小说卡片（展示章节数、状态）
│   │   ├── FileUpload.vue     # 文件上传组件（拖拽 + 选择）
│   │   ├── ConvertButton.vue  # 转换按钮（含参数配置弹窗）
│   │   ├── TaskProgress.vue   # 任务进度条（实时更新）
│   │   ├── ChapterList.vue    # 章节列表（可折叠）
│   │   └── ResultViewer.vue   # 结果查看器（YAML 语法高亮 + Markdown 预览）
│   └── styles/
│       └── main.css           # 全局样式
└── public/
    └── favicon.ico
```

## 页面设计

### 1. 首页 (Home.vue)
- 顶部导航栏：novel2script Logo + 导航
- 主区域：小说卡片网格
  - 每个卡片显示：小说名、章节数、总字数、是否有角色文件
  - 卡片点击进入详情页
- 右上角：上传按钮（触发文件上传弹窗）

### 2. 小说详情页 (NovelDetail.vue)
- 左侧：小说信息面板（名称、章节数、编码分布、角色文件状态）
- 右侧：章节列表（可折叠展开查看摘要）
- 底部：操作栏
  - 「开始转换」按钮 → 弹出参数配置
  - 参数：选择章节范围、是否增量模式
  - 转换中：显示实时进度条

### 3. 结果页 (Result.vue)
- 左侧：文件树（YAML 脚本、角色卡片、各章 Markdown）
- 右侧：内容预览
  - YAML：语法高亮显示
  - Markdown：渲染为 HTML 预览
- 顶部：下载按钮（单文件 / 打包下载）

## API 接口（对接后端 FastAPI）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/novels | 列出所有小说 |
| GET | /api/v1/novels/{name} | 获取小说详情 |
| POST | /api/v1/novels/upload | 上传小说文件 |
| DELETE | /api/v1/novels/{name} | 删除小说 |
| POST | /api/v1/convert | 发起转换任务 |
| GET | /api/v1/tasks/{task_id} | 查询任务状态 |
| GET | /api/v1/tasks/{task_id}/progress | SSE 实时进度 |
| GET | /api/v1/novels/{name}/output | 获取输出文件列表 |
| GET | /api/v1/novels/{name}/output/{file} | 下载/预览输出文件 |

## 组件数据流

```
Home.vue
  └─ NovelCard.vue ← novels (API: GET /novels)
  └─ FileUpload.vue → POST /novels/upload → 刷新列表

NovelDetail.vue
  └─ ChapterList.vue ← chapters (API: GET /novels/{name})
  └─ ConvertButton.vue → POST /convert → 轮询进度
  └─ TaskProgress.vue ← task_id (SSE: /tasks/{id}/progress)

Result.vue
  └─ ResultViewer.vue ← files (API: GET /novels/{name}/output)
```

## 交互流程

1. 用户打开首页 → 加载小说列表
2. 点击上传 → 拖拽/选择 .txt 文件 → 上传到 novels/{name}/origin/
3. 点击小说卡片 → 进入详情页 → 看到章节列表
4. 点击「开始转换」→ 选择参数 → 发起 POST /convert
5. 进度条实时更新（SSE 或轮询）
6. 转换完成 → 自动跳转结果页
7. 结果页预览 YAML/Markdown → 点击下载

## 样式规范

- 深色主题为主（类似 GitHub Dark）
- 卡片式布局，圆角 8px
- 主色调：#4FC08D (Vue 绿) + #1a1a2e (背景)
- 等宽字体用于代码/YAML 预览
