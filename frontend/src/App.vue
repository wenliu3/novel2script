<template>
  <div class="app">
    <nav class="navbar">
      <span class="logo">📜 novel2script</span>
      <span class="subtitle">中文小说 → LRM 剧本</span>
      <button class="btn-schema" @click="showSchema = true">📖 格式规范</button>
    </nav>

    <!-- 格式规范弹窗 -->
    <div v-if="showSchema" class="modal-overlay" @click.self="showSchema = false">
      <div class="modal">
        <div class="modal-header">
          <h2>📋 LRM 剧本 YAML 格式规范</h2>
          <button class="modal-close" @click="showSchema = false">&times;</button>
        </div>
        <div class="modal-body">
          <p class="schema-intro">本剧本采用 YAML 格式，层级结构为：<strong>剧本 → 章节 → 场景 → 内容</strong>（动作/对白）。英文 key 保证工具链兼容，中文 value 方便阅读和编辑。</p>

          <section>
            <h3>顶层 Screenplay</h3>
            <pre class="schema-code">title: 遮天                          # 剧本标题（来自小说名称）
author: 辰东                          # 原著作者（可选）
genre: 仙侠                           # 类型：仙侠/武侠/都市/奇幻 等（可选）
characters:                           # 角色备忘录
  叶凡: 主角，大学生
  庞博: 叶凡的好友
chapters:                             # 章节列表（见下）
  - ...</pre>
            <table class="schema-table">
              <thead><tr><th>字段</th><th>类型</th><th>必填</th><th>说明</th></tr></thead>
              <tbody>
                <tr><td><code>title</code></td><td>string</td><td>✅</td><td>剧本标题，默认"未命名剧本"</td></tr>
                <tr><td><code>author</code></td><td>string</td><td>❌</td><td>原著作者</td></tr>
                <tr><td><code>genre</code></td><td>string</td><td>❌</td><td>类型标签：仙侠/武侠/都市/奇幻 等</td></tr>
                <tr><td><code>characters</code></td><td>map</td><td>❌</td><td>角色名 → 简介，供快速查阅</td></tr>
                <tr><td><code>chapters</code></td><td>array</td><td>✅</td><td>章节列表，可为空数组</td></tr>
              </tbody>
            </table>
          </section>

          <section>
            <h3>章节 Chapter</h3>
            <pre class="schema-code">chapters:
  - chapter_number: 87               # 原著章节编号（保留原始值）
    title: 九龙拉棺                   # 章节简短标题
    chapter_title: 第087章 九龙拉棺   # 原著完整章节名（含"第X章"前缀）
    scenes:
      - ...</pre>
            <table class="schema-table">
              <thead><tr><th>字段</th><th>类型</th><th>必填</th><th>说明</th></tr></thead>
              <tbody>
                <tr><td><code>chapter_number</code></td><td>int</td><td>✅</td><td>原著章节编号，不重新排序</td></tr>
                <tr><td><code>title</code></td><td>string</td><td>❌</td><td>章节简短标题</td></tr>
                <tr><td><code>chapter_title</code></td><td>string</td><td>❌</td><td>原著完整章节名（含"第X章"前缀）</td></tr>
                <tr><td><code>scenes</code></td><td>array</td><td>✅</td><td>场景列表，可为空数组</td></tr>
              </tbody>
            </table>
          </section>

          <section>
            <h3>场景 Scene</h3>
            <pre class="schema-code">scenes:
  - scene_number: 1                  # 章节内序号，从 1 开始
    heading: "外景 宇宙深处 - 夜晚"   # 场景标题，格式：内景/外景 地点 - 时间
    int_ext: 外景                     # 内景 或 外景
    location: 宇宙深处                # 地点名称
    time_of_day: 夜晚                 # 白天 / 夜晚 / 黄昏 / 清晨 等
    characters:                       # 本场景出场角色
      - 宇航员
    summary: 旅行者二号发现九具龙尸    # 一句话概括（可选）
    content:                          # 动作和对白的有序列表（见下）
      - ...</pre>
            <table class="schema-table">
              <thead><tr><th>字段</th><th>类型</th><th>必填</th><th>说明</th></tr></thead>
              <tbody>
                <tr><td><code>scene_number</code></td><td>int</td><td>✅</td><td>章节内序号</td></tr>
                <tr><td><code>heading</code></td><td>string</td><td>✅</td><td>场景标题，遵循"内景/外景 地点 - 时间"格式</td></tr>
                <tr><td><code>int_ext</code></td><td>string</td><td>❌</td><td><code>内景</code> 或 <code>外景</code>，<code>heading</code> 的结构化拆解</td></tr>
                <tr><td><code>location</code></td><td>string</td><td>❌</td><td>地点，<code>heading</code> 的结构化拆解</td></tr>
                <tr><td><code>time_of_day</code></td><td>string</td><td>❌</td><td>时间段，<code>heading</code> 的结构化拆解</td></tr>
                <tr><td><code>characters</code></td><td>array&lt;string&gt;</td><td>❌</td><td>出场角色名列表</td></tr>
                <tr><td><code>summary</code></td><td>string</td><td>❌</td><td>场景一句话概括</td></tr>
                <tr><td><code>content</code></td><td>array</td><td>✅</td><td>动作与对白的有序列表，可为空数组</td></tr>
              </tbody>
            </table>
          </section>

          <section>
            <h3>内容条目 — 动作 Action</h3>
            <pre class="schema-code">content:
  - type: action
    text: 冰冷与黑暗并存的宇宙深处，九具庞大的龙尸拉着一口青铜古棺缓缓漂移。</pre>
            <table class="schema-table">
              <thead><tr><th>字段</th><th>类型</th><th>必填</th><th>说明</th></tr></thead>
              <tbody>
                <tr><td><code>type</code></td><td><code>"action"</code></td><td>✅</td><td>固定值，用于区分条目类型</td></tr>
                <tr><td><code>text</code></td><td>string</td><td>✅</td><td>动作或场景描述，可多句</td></tr>
              </tbody>
            </table>
          </section>

          <section>
            <h3>内容条目 — 对白 Dialogue</h3>
            <pre class="schema-code">content:
  - type: dialogue
    character: 宇航员
    text: 上帝，我看到了什么？
    parenthetical: 颤抖着          # 表演提示，可选</pre>
            <table class="schema-table">
              <thead><tr><th>字段</th><th>类型</th><th>必填</th><th>说明</th></tr></thead>
              <tbody>
                <tr><td><code>type</code></td><td><code>"dialogue"</code></td><td>✅</td><td>固定值，用于区分条目类型</td></tr>
                <tr><td><code>character</code></td><td>string</td><td>✅</td><td>说话的角色名，与顶层 <code>characters</code> 对应</td></tr>
                <tr><td><code>text</code></td><td>string</td><td>✅</td><td>对白内容</td></tr>
                <tr><td><code>parenthetical</code></td><td>string</td><td>❌</td><td>括号内的表演提示，如"低声"、"激动地"</td></tr>
              </tbody>
            </table>
          </section>

          <section>
            <h3>完整示例</h3>
            <pre class="schema-code">title: 遮天
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
            text: 叶凡拎起背包，头也不回地走出宿舍。</pre>
          </section>
        </div>
      </div>
    </div>

    <!-- 步骤条（转换流程才显示） -->
    <div v-if="step !== 'upload' && step !== 'yaml-visual'" class="stepper">
      <div class="stepper-item" :class="{ active: stepIndex >= 0, done: stepIndex > 0 }">
        <span class="stepper-num">1</span>
        <span class="stepper-label">上传小说</span>
      </div>
      <div class="stepper-line" :class="{ active: stepIndex > 0 }"></div>
      <div class="stepper-item" :class="{ active: stepIndex >= 1, done: stepIndex > 1 }">
        <span class="stepper-num">2</span>
        <span class="stepper-label">AI 转换</span>
      </div>
      <div class="stepper-line" :class="{ active: stepIndex > 1 }"></div>
      <div class="stepper-item" :class="{ active: stepIndex >= 2 }">
        <span class="stepper-num">3</span>
        <span class="stepper-label">预览下载</span>
      </div>
    </div>

    <main class="main">

      <!-- 首页：两个功能入口 -->
      <template v-if="step === 'upload'">
        <div class="feature-grid">
          <!-- 功能1：小说转剧本 -->
          <div class="card feature-card">
            <div class="feature-icon">📄</div>
            <h2>小说转剧本</h2>
            <p class="feature-desc">上传 TXT 小说文件，AI 自动转换为结构化 YAML 剧本</p>
            <div class="form-group">
              <label>小说名称</label>
              <input v-model="novelName" placeholder="如：神雕侠侣" />
            </div>
            <div class="upload-area" @dragover.prevent @drop.prevent="onDrop">
              <input type="file" accept=".txt" @change="onFileChange" ref="fileInput" id="file-input" hidden />
              <label for="file-input" class="upload-label">
                <template v-if="selectedFile">
                  <span class="file-name">📎 {{ selectedFile.name }} ({{ (selectedFile.size / 1024).toFixed(1) }}KB)</span>
                  <span class="file-change">重新选择</span>
                </template>
                <template v-else>
                  <span class="upload-icon">📁</span>
                  <span>点击选择 TXT 文件，或拖拽到此处</span>
                </template>
              </label>
            </div>
            <button class="btn-primary" :disabled="!canUpload" @click="doUpload">
              {{ uploading ? '上传中...' : '上传并开始转换' }}
            </button>
          </div>

          <!-- 功能2：YAML 可视化预览 -->
          <div class="card feature-card">
            <div class="feature-icon">🎬</div>
            <h2>剧本可视化</h2>
            <p class="feature-desc">上传已有的 YAML 剧本文件，以可视化剧本排版展示</p>
            <div class="upload-area upload-area-alt" @dragover.prevent @drop.prevent="onYamlDrop">
              <input type="file" accept=".yaml,.yml" @change="onYamlFileChange" id="yaml-input" hidden />
              <label for="yaml-input" class="upload-label">
                <template v-if="selectedYamlFile">
                  <span class="file-name">📎 {{ selectedYamlFile.name }}</span>
                  <span class="file-change">重新选择</span>
                </template>
                <template v-else>
                  <span class="upload-icon">📋</span>
                  <span>点击选择 YAML 文件，或拖拽到此处</span>
                </template>
              </label>
            </div>
            <button class="btn-secondary" :disabled="!selectedYamlFile" @click="doLoadYaml">
              查看剧本
            </button>
          </div>
        </div>
      </template>

      <!-- Step 2: 进度 -->
      <section v-if="step === 'progress'" class="card">
        <h2>⏳ 转换中...</h2>
        <div class="progress-info">
          <div class="message">{{ taskMessage }}</div>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <div class="progress-pulse">
          <span></span><span></span><span></span>
        </div>
        <p class="hint">处理时间取决于小说长度，百万字小说约需 5-15 分钟</p>
      </section>

      <!-- Step 3: 完成 + 预览 -->
      <section v-if="step === 'done'" class="card success">
        <h2>✅ 转换完成</h2>
        <p>转换完成，可进行预览或者下载</p>

        <div v-if="previewLoading" class="preview-loading">⏳ 加载预览中...</div>
        <template v-else-if="yamlContent">
          <!-- 视图切换 -->
          <div class="view-toggle">
            <button
              class="toggle-btn" :class="{ active: viewMode === 'visual' }"
              @click="viewMode = 'visual'"
            >📖 剧本视图</button>
            <button
              class="toggle-btn" :class="{ active: viewMode === 'raw' }"
              @click="viewMode = 'raw'"
            >{ } 原始 YAML</button>
          </div>

          <!-- 可视化剧本 -->
          <div v-if="viewMode === 'visual'" class="preview-area">
            <div v-if="parsedData" class="screenplay-wrapper">
              <ScreenplayView :data="parsedData" />
            </div>
            <div v-else class="preview-loading">YAML 解析失败，请切换到原始视图查看</div>
          </div>

          <!-- 原始 YAML -->
          <div v-else class="preview-area">
            <div class="preview-header">
              <span>📋 YAML 预览</span>
              <button class="btn-copy" @click="copyYaml">复制</button>
            </div>
            <pre class="preview-content">{{ yamlContent }}</pre>
          </div>
        </template>

        <button class="btn-primary" @click="doDownload">📥 下载 YAML 剧本</button>
        <button class="btn-secondary" @click="reset">转换另一本</button>
      </section>

      <!-- 失败 -->
      <section v-if="step === 'failed'" class="card error">
        <h2>❌ 转换失败</h2>
        <p>{{ taskMessage }}</p>
        <button class="btn-secondary" @click="reset">重试</button>
      </section>

      <!-- YAML 可视化预览（独立功能） -->
      <section v-if="step === 'yaml-visual'" class="card">
        <div class="yaml-visual-header">
          <h2>🎬 剧本预览</h2>
          <button class="btn-back" @click="reset">← 返回</button>
        </div>

        <div class="view-toggle">
          <button class="toggle-btn" :class="{ active: viewMode === 'visual' }" @click="viewMode = 'visual'">📖 剧本视图</button>
          <button class="toggle-btn" :class="{ active: viewMode === 'raw' }" @click="viewMode = 'raw'">{ } 原始 YAML</button>
        </div>

        <div v-if="viewMode === 'visual'" class="preview-area">
          <div v-if="parsedData" class="screenplay-wrapper">
            <ScreenplayView :data="parsedData" />
          </div>
          <div v-else class="preview-loading">YAML 解析失败，请切换到原始视图查看</div>
        </div>

        <div v-else class="preview-area">
          <div class="preview-header">
            <span>📋 YAML 预览</span>
            <button class="btn-copy" @click="copyYaml">复制</button>
          </div>
          <pre class="preview-content">{{ yamlContent }}</pre>
        </div>
      </section>

    </main>

    <footer class="footer">
      <span>novel2script — AI 辅助剧本创作工具</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import yaml from 'js-yaml'
import ScreenplayView from './components/ScreenplayView.vue'
import { uploadNovelFiles, startConvert, fetchTaskStatus, previewYaml, downloadYaml } from './api'

const step = ref('upload')
const stepIndex = computed(() => {
  if (step.value === 'upload') return 0
  if (step.value === 'progress') return 1
  return 2 // done / failed
})

const novelName = ref('')
const selectedFile = ref(null)
const uploading = ref(false)
const converting = ref(false)
const taskId = ref('')
const taskStatus = ref('')
const taskMessage = ref('')
const progressPercent = ref(0)
const yamlContent = ref('')
const previewLoading = ref(false)
const showSchema = ref(false)
const viewMode = ref('visual') // 'visual' | 'raw'

const parsedData = computed(() => {
  if (!yamlContent.value) return null
  try {
    return yaml.load(yamlContent.value)
  } catch {
    return null
  }
})

const canUpload = computed(() => novelName.value.trim() && selectedFile.value && !uploading.value)

const selectedYamlFile = ref(null)

function onFileChange(e) {
  const f = e.target.files[0]
  if (f) selectedFile.value = f
}

function onDrop(e) {
  const f = e.dataTransfer.files[0]
  if (f && f.name.endsWith('.txt')) {
    selectedFile.value = f
  }
}

function onYamlFileChange(e) {
  const f = e.target.files[0]
  if (f) selectedYamlFile.value = f
}

function onYamlDrop(e) {
  const f = e.dataTransfer.files[0]
  if (f && (f.name.endsWith('.yaml') || f.name.endsWith('.yml'))) {
    selectedYamlFile.value = f
  }
}

function doLoadYaml() {
  const file = selectedYamlFile.value
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    yamlContent.value = e.target.result
    viewMode.value = 'visual'
    step.value = 'yaml-visual'
  }
  reader.readAsText(file)
}

// 合并：上传后直接开始转换
async function doUpload() {
  uploading.value = true
  try {
    const result = await uploadNovelFiles(novelName.value.trim(), [selectedFile.value])
    novelName.value = result.novel_name
    // 上传成功，直接发起转换
    const convertResult = await startConvert(novelName.value)
    taskId.value = convertResult.task_id
    step.value = 'progress'
    pollStatus()
  } catch (e) {
    alert('操作失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
}

function pollStatus() {
  let retries = 0
  const maxRetries = 300
  const timer = setInterval(async () => {
    retries++
    if (retries > maxRetries) {
      clearInterval(timer)
      taskMessage.value = '轮询超时，请刷新页面查看结果'
      step.value = 'failed'
      return
    }
    try {
      const result = await fetchTaskStatus(taskId.value)
      taskStatus.value = result.status
      taskMessage.value = result.message || result.progress || ''

      if (result.progress) {
        const match = result.progress.match(/(\d+)\/(\d+)/)
        if (match) {
          progressPercent.value = Math.round((parseInt(match[1]) / parseInt(match[2])) * 100)
        }
      }

      if (result.status === 'completed') {
        clearInterval(timer)
        step.value = 'done'
        progressPercent.value = 100
        fetchPreview()
      } else if (result.status === 'failed') {
        clearInterval(timer)
        step.value = 'failed'
      }
    } catch (e) {
      console.error('轮询失败:', e)
    }
  }, 3000)
}

async function fetchPreview() {
  previewLoading.value = true
  try {
    const data = await previewYaml(novelName.value)
    yamlContent.value = data.content
  } catch (e) {
    yamlContent.value = '# 预览加载失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    previewLoading.value = false
  }
}

async function copyYaml() {
  try {
    await navigator.clipboard.writeText(yamlContent.value)
    alert('已复制到剪贴板')
  } catch {
    alert('复制失败，请手动选择复制')
  }
}

function doDownload() {
  downloadYaml(novelName.value)
}

function reset() {
  step.value = 'upload'
  novelName.value = ''
  selectedFile.value = null
  selectedYamlFile.value = null
  taskId.value = ''
  taskStatus.value = ''
  taskMessage.value = ''
  progressPercent.value = 0
  yamlContent.value = ''
  previewLoading.value = false
  viewMode.value = 'visual'
}
</script>

<style>
:root {
  --primary: #6366f1;
  --primary-hover: #4f46e5;
  --primary-light: #eef2ff;
  --primary-glow: rgba(99, 102, 241, 0.15);
  --bg: #f1f5f9;
  --bg-card: #ffffff;
  --text: #1e293b;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --success: #10b981;
  --success-light: #ecfdf5;
  --error: #ef4444;
  --error-light: #fef2f2;
  --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  --gradient-bg: linear-gradient(180deg, #eef2ff 0%, #f1f5f9 40%);
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--gradient-bg); color: var(--text); min-height: 100vh;
}
</style>

<style scoped>
.app {
  min-height: 100vh; display: flex; flex-direction: column;
}

/* 导航栏 */
.navbar {
  display: flex; align-items: center; gap: 16px;
  padding: 14px 28px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  position: sticky; top: 0; z-index: 100;
  backdrop-filter: blur(8px);
}
.logo {
  font-size: 20px; font-weight: 800;
  background: var(--gradient-primary); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.subtitle { color: var(--text-muted); font-size: 13px; letter-spacing: 0.02em; }
.btn-schema {
  margin-left: auto; background: var(--primary-light); color: var(--primary);
  border: none; padding: 7px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 500; cursor: pointer; white-space: nowrap;
  transition: all 0.2s;
}
.btn-schema:hover { background: var(--primary); color: white; box-shadow: 0 2px 8px var(--primary-glow); }

/* 步骤条 */
.stepper {
  display: flex; align-items: center; justify-content: center;
  gap: 0; padding: 28px 24px 0; max-width: 640px; margin: 0 auto;
}
.stepper-item {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: var(--text-muted); transition: color 0.3s;
}
.stepper-item.active { color: var(--text); font-weight: 500; }
.stepper-item.done { color: var(--primary); }
.stepper-num {
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600;
  border: 2px solid var(--border); color: var(--text-muted);
  transition: all 0.3s; background: var(--bg-card);
}
.stepper-item.active .stepper-num {
  border-color: var(--primary); background: var(--primary-light); color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}
.stepper-item.done .stepper-num {
  border-color: var(--primary); background: var(--gradient-primary); color: white;
}
.stepper-label { font-weight: 500; }
.stepper-line {
  width: 60px; height: 2px; background: var(--border);
  margin: 0 8px; transition: background 0.3s;
}
.stepper-line.active { background: var(--gradient-primary); }

/* 主区域 */
.main { flex: 1; max-width: 960px; width: 100%; margin: 28px auto; padding: 0 24px; }

/* 首页双卡 */
.feature-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
}
@media (max-width: 768px) {
  .feature-grid { grid-template-columns: 1fr; }
}
.feature-card {
  background: var(--bg-card); border-radius: 16px; padding: 32px;
  border: 1px solid var(--border); box-shadow: var(--shadow-md);
}
.feature-icon { font-size: 32px; margin-bottom: 12px; }
.feature-card h2 { margin-bottom: 8px; font-size: 18px; font-weight: 700; }
.feature-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; line-height: 1.5; }
.upload-area-alt {
  background: #faf5ff; border-color: #e9d5ff;
}
.upload-area-alt:hover {
  border-color: #a855f7; background: #f5f3ff;
}

/* 非首页卡片 */
.card {
  background: var(--bg-card); border-radius: 16px; padding: 36px;
  border: 1px solid var(--border); box-shadow: var(--shadow-md);
  max-width: 640px; margin: 0 auto; width: 100%;
}
.card h2 { margin-bottom: 24px; font-size: 20px; font-weight: 700; }
.card.success { border-color: var(--success); background: var(--success-light); }
.card.error { border-color: var(--error); background: var(--error-light); }

/* 表单 */
.form-group { margin-bottom: 20px; }
.form-group label { display: block; margin-bottom: 8px; font-size: 14px; font-weight: 500; color: var(--text-muted); }
.form-group input[type="text"], .form-group input:not([type]) {
  width: 100%; padding: 11px 14px; border: 1.5px solid var(--border); border-radius: 10px;
  font-size: 15px; transition: border-color 0.2s, box-shadow 0.2s; outline: none;
}
.form-group input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}
.form-group input[type="file"] { font-size: 14px; }

/* 上传区域 */
.upload-area {
  border: 2px dashed var(--border); border-radius: 12px;
  padding: 36px 20px; text-align: center; margin-bottom: 20px;
  transition: all 0.2s; cursor: pointer;
  background: var(--bg);
}
.upload-area:hover {
  border-color: var(--primary); background: var(--primary-light);
  box-shadow: 0 0 0 3px var(--primary-glow);
}
.upload-label {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  font-size: 14px; color: var(--text-muted); cursor: pointer;
}
.upload-icon { font-size: 36px; }
.file-name { font-size: 14px; color: var(--text); font-weight: 600; }
.file-change { font-size: 12px; color: var(--primary); font-weight: 500; }

/* 按钮 */
.btn-primary {
  background: var(--gradient-primary); color: white; border: none; padding: 13px 24px;
  border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; width: 100%;
  transition: all 0.2s; box-shadow: 0 2px 8px var(--primary-glow);
  letter-spacing: 0.02em;
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3);
}
.btn-primary:active { transform: translateY(0); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }
.btn-secondary {
  background: var(--bg-card); color: var(--text-muted); border: 1.5px solid var(--border);
  padding: 11px 24px; border-radius: 10px; font-size: 14px; cursor: pointer;
  margin-top: 12px; width: 100%; font-weight: 500;
  transition: all 0.2s;
}
.btn-secondary:hover { border-color: var(--primary); color: var(--primary); }

/* 进度 */
.progress-info { margin-bottom: 20px; }
.message { font-size: 14px; color: var(--text-muted); word-break: break-all; line-height: 1.6; }
.progress-bar {
  height: 10px; background: var(--border); border-radius: 5px; overflow: hidden; margin-bottom: 20px;
}
.progress-fill {
  height: 100%; border-radius: 5px; transition: width 0.4s ease;
  background: var(--gradient-primary);
}
.hint { font-size: 12px; color: var(--text-muted); line-height: 1.5; }

/* 进度脉冲动画 */
.progress-pulse {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; margin-bottom: 20px;
}
.progress-pulse span {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--primary); animation: pulse 1.4s ease-in-out infinite;
}
.progress-pulse span:nth-child(2) { animation-delay: 0.2s; }
.progress-pulse span:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

/* 预览 */
.view-toggle {
  display: flex; gap: 0; margin: 20px 0 16px;
  background: var(--bg); border-radius: 10px; padding: 4px;
}
.toggle-btn {
  flex: 1; padding: 9px 16px; border: none; border-radius: 8px;
  font-size: 13px; font-weight: 500; cursor: pointer;
  background: transparent; color: var(--text-muted);
  transition: all 0.2s;
}
.toggle-btn.active {
  background: var(--bg-card); color: var(--primary);
  box-shadow: var(--shadow-sm);
}
.toggle-btn:hover:not(.active) { color: var(--text); }
.screenplay-wrapper {
  max-height: 520px; overflow-y: auto; padding: 24px;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
  margin: 16px 0;
}
.preview-loading {
  padding: 24px; text-align: center; color: var(--text-muted); font-size: 14px;
  background: var(--bg); border-radius: 10px; margin-bottom: 20px;
}
.preview-area { margin: 20px 0; }
.preview-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px; font-size: 14px; font-weight: 500; color: var(--text-muted);
}
.btn-copy {
  background: var(--primary-light); color: var(--primary); border: none;
  padding: 5px 14px; border-radius: 6px; font-size: 12px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
}
.btn-copy:hover { background: var(--primary); color: white; }
.preview-content {
  background: #1e293b; color: #e2e8f0; padding: 20px; border-radius: 10px;
  font-size: 13px; line-height: 1.6; overflow: auto; max-height: 400px;
  white-space: pre-wrap; word-break: break-all; tab-size: 2;
  font-family: "JetBrains Mono", "Fira Code", "SF Mono", Menlo, monospace;
}

/* 弹窗 */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: var(--bg-card); border-radius: 16px; width: 90%; max-width: 720px;
  max-height: 85vh; display: flex; flex-direction: column;
  box-shadow: 0 24px 64px rgba(0,0,0,0.2);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 22px 28px; border-bottom: 1px solid var(--border);
}
.modal-header h2 { font-size: 18px; margin: 0; font-weight: 700; }
.modal-close {
  background: var(--bg); border: none; font-size: 20px; cursor: pointer;
  color: var(--text-muted); width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s; line-height: 1;
}
.modal-close:hover { background: var(--error-light); color: var(--error); }
.modal-body {
  padding: 28px; overflow-y: auto; font-size: 14px; line-height: 1.6;
}
.modal-body section { margin-bottom: 32px; }
.modal-body section:last-child { margin-bottom: 0; }
.modal-body h3 { font-size: 16px; margin-bottom: 14px; color: var(--primary); font-weight: 600; }
.schema-code {
  background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 10px;
  font-size: 12px; line-height: 1.6; overflow-x: auto; margin-bottom: 14px;
  white-space: pre; tab-size: 2;
  font-family: "JetBrains Mono", "Fira Code", "SF Mono", Menlo, monospace;
}
.schema-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.schema-table th, .schema-table td {
  text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border);
}
.schema-table th { color: var(--text-muted); font-weight: 500; font-size: 12px; letter-spacing: 0.03em; }
.schema-table code {
  background: var(--primary-light); color: var(--primary); padding: 2px 7px; border-radius: 5px; font-size: 12px;
  font-family: "JetBrains Mono", "Fira Code", "SF Mono", Menlo, monospace;
}
.schema-intro {
  font-size: 13px; color: #475569; line-height: 1.8;
  background: var(--primary-light); border: 1px solid #c7d2fe; border-radius: 10px;
  padding: 16px 18px; margin-bottom: 28px;
}

/* 底部 */
.footer {
  text-align: center; padding: 24px; font-size: 12px; color: var(--text-muted);
  border-top: 1px solid var(--border); margin-top: auto;
  letter-spacing: 0.02em;
}
.yaml-visual-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px;
}
.yaml-visual-header h2 { margin-bottom: 0; }
.btn-back {
  background: none; border: none; color: var(--primary); font-size: 14px;
  font-weight: 500; cursor: pointer; padding: 6px 12px; border-radius: 6px;
  transition: background 0.2s;
}
.btn-back:hover { background: var(--primary-light); }
</style>
