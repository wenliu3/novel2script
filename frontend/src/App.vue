<template>
  <div class="app">
    <nav class="navbar">
      <span class="logo">📜 novel2script</span>
      <span class="subtitle">中文小说 → LRM 剧本</span>
    </nav>
    <main class="main">

      <!-- Step 1: 上传 -->
      <section v-if="step === 'upload'" class="card">
        <h2>📄 上传小说</h2>
        <div class="form-group">
          <label>小说名称</label>
          <input v-model="novelName" placeholder="如：神雕侠侣" />
        </div>
        <div class="form-group">
          <label>选择 TXT 文件（可多选）</label>
          <input type="file" multiple accept=".txt" @change="onFileChange" />
        </div>
        <div v-if="files.length" class="file-list">
          <div v-for="f in files" :key="f.name">📎 {{ f.name }} ({{ (f.size / 1024).toFixed(1) }}KB)</div>
        </div>
        <button class="btn-primary" :disabled="!canUpload" @click="doUpload">
          {{ uploading ? '上传中...' : '上传' }}
        </button>
      </section>

      <!-- Step 2: 转换 -->
      <section v-if="step === 'convert'" class="card">
        <h2>🎬 开始转换</h2>
        <p>小说「<strong>{{ novelName }}</strong>」已上传</p>
        <button class="btn-primary" :disabled="converting" @click="doConvert">
          {{ converting ? '提交中...' : '开始转换' }}
        </button>
      </section>

      <!-- Step 3: 进度 -->
      <section v-if="step === 'progress'" class="card">
        <h2>⏳ 转换中...</h2>
        <div class="progress-info">
          <div class="status">{{ taskStatus }}</div>
          <div class="message">{{ taskMessage }}</div>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <p class="hint">处理时间取决于小说长度，百万字小说约需 5-15 分钟</p>
      </section>

      <!-- Step 4: 完成 -->
      <section v-if="step === 'done'" class="card success">
        <h2>✅ 转换完成</h2>
        <p>{{ taskMessage }}</p>
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
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { uploadNovelFiles, startConvert, fetchTaskStatus, downloadYaml } from './api'

const step = ref('upload')
const novelName = ref('')
const files = ref([])
const uploading = ref(false)
const converting = ref(false)
const taskId = ref('')
const taskStatus = ref('')
const taskMessage = ref('')
const progressPercent = ref(0)

const canUpload = computed(() => novelName.value.trim() && files.value.length > 0 && !uploading.value)

function onFileChange(e) {
  files.value = Array.from(e.target.files)
}

async function doUpload() {
  uploading.value = true
  try {
    const result = await uploadNovelFiles(novelName.value.trim(), files.value)
    novelName.value = result.novel_name
    step.value = 'convert'
  } catch (e) {
    alert('上传失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
}

async function doConvert() {
  converting.value = true
  try {
    const result = await startConvert(novelName.value)
    taskId.value = result.task_id
    step.value = 'progress'
    pollStatus()
  } catch (e) {
    alert('转换失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    converting.value = false
  }
}

function pollStatus() {
  let retries = 0
  const maxRetries = 300 // 最多 15 分钟 (300 × 3s)
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
      } else if (result.status === 'failed') {
        clearInterval(timer)
        step.value = 'failed'
      }
    } catch (e) {
      console.error('轮询失败:', e)
    }
  }, 3000)
}

function doDownload() {
  downloadYaml(novelName.value)
}

function reset() {
  step.value = 'upload'
  novelName.value = ''
  files.value = []
  taskId.value = ''
  taskStatus.value = ''
  taskMessage.value = ''
  progressPercent.value = 0
}
</script>

<style>
:root {
  --primary: #4f46e5;
  --primary-hover: #4338ca;
  --bg: #f8fafc;
  --bg-card: #ffffff;
  --text: #1e293b;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --success: #10b981;
  --error: #ef4444;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }
</style>

<style scoped>
.navbar {
  display: flex; align-items: center; gap: 16px;
  padding: 12px 24px; background: var(--bg-card); border-bottom: 1px solid var(--border);
}
.logo { font-size: 20px; font-weight: 700; color: var(--primary); }
.subtitle { color: var(--text-muted); font-size: 13px; }
.main { max-width: 640px; margin: 40px auto; padding: 0 24px; }
.card {
  background: var(--bg-card); border-radius: 12px; padding: 32px;
  border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.card h2 { margin-bottom: 20px; font-size: 20px; }
.card.success { border-color: var(--success); }
.card.error { border-color: var(--error); }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: var(--text-muted); }
.form-group input[type="text"], .form-group input:not([type]) {
  width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 15px;
}
.form-group input[type="file"] { font-size: 14px; }
.file-list { margin-bottom: 16px; font-size: 13px; color: var(--text-muted); }
.file-list div { padding: 4px 0; }
.btn-primary {
  background: var(--primary); color: white; border: none; padding: 12px 24px;
  border-radius: 8px; font-size: 15px; font-weight: 500; cursor: pointer; width: 100%;
}
.btn-primary:hover { background: var(--primary-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  background: transparent; color: var(--text-muted); border: 1px solid var(--border);
  padding: 10px 24px; border-radius: 8px; font-size: 14px; cursor: pointer;
  margin-top: 12px; width: 100%;
}
.btn-secondary:hover { border-color: var(--text-muted); }
.progress-info { margin-bottom: 16px; }
.status { font-weight: 600; margin-bottom: 4px; }
.message { font-size: 14px; color: var(--text-muted); word-break: break-all; }
.progress-bar {
  height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; margin-bottom: 12px;
}
.progress-fill { height: 100%; background: var(--primary); border-radius: 4px; transition: width 0.3s; }
.hint { font-size: 12px; color: var(--text-muted); }
</style>
