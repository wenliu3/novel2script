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

    <!-- 步骤条 -->
    <div class="stepper">
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

      <!-- Step 1: 上传 + 转换（合并） -->
      <section v-if="step === 'upload'" class="card">
        <h2>📄 上传小说</h2>
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
      </section>

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
        <div v-else-if="yamlContent" class="preview-area">
          <div class="preview-header">
            <span>📋 YAML 预览</span>
            <button class="btn-copy" @click="copyYaml">复制</button>
          </div>
          <pre class="preview-content">{{ yamlContent }}</pre>
        </div>

        <button class="btn-primary" @click="doDownload">📥 下载 YAML 剧本</button>
        <button class="btn-secondary" @click="reset">转换另一本</button>
      </section>

      <!-- 失败 -->
      <section v-if="step === 'failed'" class="card error">
        <h2>❌ 转换失败</h2>
        <p>{{ taskMessage }}</p>
        <button class="btn-secondary" @click="reset">重试</button>
      </section>

    </main>

    <footer class="footer">
      <span>novel2script — AI 辅助剧本创作工具</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
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

const canUpload = computed(() => novelName.value.trim() && selectedFile.value && !uploading.value)

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
  taskId.value = ''
  taskStatus.value = ''
  taskMessage.value = ''
  progressPercent.value = 0
  yamlContent.value = ''
  previewLoading.value = false
}
</script>

<style>
:root {
  --primary: #4f46e5;
  --primary-hover: #4338ca;
  --primary-light: #eef2ff;
  --bg: #f8fafc;
  --bg-card: #ffffff;
  --text: #1e293b;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --success: #10b981;
  --error: #ef4444;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
</style>

<style scoped>
.app {
  min-height: 100vh; display: flex; flex-direction: column;
}

/* 导航栏 */
.navbar {
  display: flex; align-items: center; gap: 16px;
  padding: 12px 24px; background: var(--bg-card); border-bottom: 1px solid var(--border);
}
.logo { font-size: 20px; font-weight: 700; color: var(--primary); }
.subtitle { color: var(--text-muted); font-size: 13px; }
.btn-schema {
  margin-left: auto; background: transparent; color: var(--primary);
  border: 1px solid var(--primary); padding: 6px 14px; border-radius: 6px;
  font-size: 13px; cursor: pointer; white-space: nowrap;
}
.btn-schema:hover { background: var(--primary); color: white; }

/* 步骤条 */
.stepper {
  display: flex; align-items: center; justify-content: center;
  gap: 0; padding: 24px 24px 0; max-width: 640px; margin: 0 auto;
}
.stepper-item {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: var(--text-muted); transition: color 0.3s;
}
.stepper-item.active { color: var(--text); }
.stepper-item.done { color: var(--primary); }
.stepper-num {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600;
  border: 2px solid var(--border); color: var(--text-muted);
  transition: all 0.3s;
}
.stepper-item.active .stepper-num {
  border-color: var(--primary); background: var(--primary-light); color: var(--primary);
}
.stepper-item.done .stepper-num {
  border-color: var(--primary); background: var(--primary); color: white;
}
.stepper-label { font-weight: 500; }
.stepper-line {
  width: 60px; height: 2px; background: var(--border);
  margin: 0 8px; transition: background 0.3s;
}
.stepper-line.active { background: var(--primary); }

/* 主区域 */
.main { flex: 1; max-width: 640px; width: 100%; margin: 24px auto; padding: 0 24px; }
.card {
  background: var(--bg-card); border-radius: 12px; padding: 32px;
  border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.card h2 { margin-bottom: 20px; font-size: 20px; }
.card.success { border-color: var(--success); }
.card.error { border-color: var(--error); }

/* 表单 */
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: var(--text-muted); }
.form-group input[type="text"], .form-group input:not([type]) {
  width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 15px;
}
.form-group input[type="file"] { font-size: 14px; }

/* 上传区域 */
.upload-area {
  border: 2px dashed var(--border); border-radius: 10px;
  padding: 28px 20px; text-align: center; margin-bottom: 16px;
  transition: border-color 0.2s, background 0.2s; cursor: pointer;
}
.upload-area:hover { border-color: var(--primary); background: var(--primary-light); }
.upload-label {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  font-size: 14px; color: var(--text-muted); cursor: pointer;
}
.upload-icon { font-size: 32px; }
.file-name { font-size: 14px; color: var(--text); font-weight: 500; }
.file-change { font-size: 12px; color: var(--primary); }

/* 按钮 */
.btn-primary {
  background: var(--primary); color: white; border: none; padding: 12px 24px;
  border-radius: 8px; font-size: 15px; font-weight: 500; cursor: pointer; width: 100%;
  transition: background 0.2s;
}
.btn-primary:hover { background: var(--primary-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  background: transparent; color: var(--text-muted); border: 1px solid var(--border);
  padding: 10px 24px; border-radius: 8px; font-size: 14px; cursor: pointer;
  margin-top: 12px; width: 100%;
}
.btn-secondary:hover { border-color: var(--text-muted); }

/* 进度 */
.progress-info { margin-bottom: 16px; }
.message { font-size: 14px; color: var(--text-muted); word-break: break-all; }
.progress-bar {
  height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; margin-bottom: 16px;
}
.progress-fill { height: 100%; background: var(--primary); border-radius: 4px; transition: width 0.3s; }
.hint { font-size: 12px; color: var(--text-muted); }

/* 进度脉冲动画 */
.progress-pulse {
  display: flex; align-items: center; justify-content: center;
  gap: 6px; margin-bottom: 16px;
}
.progress-pulse span {
  width: 8px; height: 8px; border-radius: 50%; background: var(--primary);
  animation: pulse 1.4s ease-in-out infinite;
}
.progress-pulse span:nth-child(2) { animation-delay: 0.2s; }
.progress-pulse span:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

/* 预览 */
.preview-loading {
  padding: 20px; text-align: center; color: var(--text-muted); font-size: 14px;
  background: var(--bg); border-radius: 8px; margin-bottom: 16px;
}
.preview-area { margin: 16px 0; }
.preview-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px; font-size: 14px; font-weight: 500; color: var(--text-muted);
}
.btn-copy {
  background: transparent; color: var(--primary); border: 1px solid var(--primary);
  padding: 4px 12px; border-radius: 6px; font-size: 12px; cursor: pointer;
}
.btn-copy:hover { background: var(--primary); color: white; }
.preview-content {
  background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 8px;
  font-size: 13px; line-height: 1.5; overflow: auto; max-height: 400px;
  white-space: pre-wrap; word-break: break-all; tab-size: 2;
}

/* 弹窗 */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: var(--bg-card); border-radius: 12px; width: 90%; max-width: 720px;
  max-height: 85vh; display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 24px; border-bottom: 1px solid var(--border);
}
.modal-header h2 { font-size: 18px; margin: 0; }
.modal-close {
  background: none; border: none; font-size: 24px; cursor: pointer;
  color: var(--text-muted); padding: 0 4px; line-height: 1;
}
.modal-close:hover { color: var(--text); }
.modal-body {
  padding: 24px; overflow-y: auto; font-size: 14px; line-height: 1.6;
}
.modal-body section { margin-bottom: 28px; }
.modal-body section:last-child { margin-bottom: 0; }
.modal-body h3 { font-size: 16px; margin-bottom: 12px; color: var(--primary); }
.schema-code {
  background: #1e293b; color: #e2e8f0; padding: 14px; border-radius: 8px;
  font-size: 12px; line-height: 1.5; overflow-x: auto; margin-bottom: 12px;
  white-space: pre; tab-size: 2;
}
.schema-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.schema-table th, .schema-table td {
  text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border);
}
.schema-table th { color: var(--text-muted); font-weight: 500; font-size: 12px; }
.schema-table code {
  background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 12px;
}
.schema-intro {
  font-size: 13px; color: #475569; line-height: 1.7;
  background: #f8fafc; border: 1px solid var(--border); border-radius: 8px;
  padding: 14px 16px; margin-bottom: 24px;
}

/* 底部 */
.footer {
  text-align: center; padding: 20px; font-size: 12px; color: var(--text-muted);
  border-top: 1px solid var(--border); margin-top: auto;
}
</style>
