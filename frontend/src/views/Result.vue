<template>
  <div class="result-page">
    <div class="top-bar">
      <router-link :to="`/novel/${name}`">← 返回</router-link>
      <h1>{{ name }} - 转换结果</h1>
      <button class="btn-primary" @click="handleDownload" :disabled="!yamlContent">
        📥 下载 YAML
      </button>
    </div>

    <div v-if="loading" class="empty-state">加载中...</div>

    <div v-else-if="error" class="empty-state">
      <div class="icon">❌</div>
      <p>{{ error }}</p>
    </div>

    <div v-else-if="!yamlContent" class="empty-state">
      <div class="icon">📄</div>
      <p>暂无输出文件</p>
      <p>请先完成转换</p>
    </div>

    <div v-else class="preview-area card">
      <div class="preview-header">
        <span class="mono">{{ name }}_script.yaml</span>
        <span class="line-count">{{ lineCount }} 行</span>
      </div>
      <div class="code-container">
        <div class="line-numbers">
          <span v-for="n in lineCount" :key="n">{{ n }}</span>
        </div>
        <pre class="code-content mono">{{ yamlContent }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { fetchYamlPreview, downloadYaml } from '../api'

const route = useRoute()
const name = route.params.name

const yamlContent = ref('')
const loading = ref(true)
const error = ref('')

const lineCount = computed(() => (yamlContent.value || '').split('\n').length)

async function loadYaml() {
  loading.value = true
  error.value = ''
  try {
    yamlContent.value = await fetchYamlPreview(name)
  } catch (e) {
    if (e.response?.status === 404) {
      error.value = 'YAML 文件不存在，请先完成转换'
    } else {
      error.value = '加载失败: ' + (e.response?.data?.detail || e.message)
    }
  } finally {
    loading.value = false
  }
}

function handleDownload() {
  downloadYaml(name)
}

onMounted(loadYaml)
</script>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.top-bar h1 { font-size: 22px; flex: 1; }
.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.line-count { color: var(--text-muted); }
.code-container {
  display: flex;
  background: #0d1117;
  min-height: 500px;
  max-height: 700px;
  overflow: auto;
  border-radius: 0 0 var(--radius) var(--radius);
}
.line-numbers {
  display: flex;
  flex-direction: column;
  padding: 16px 8px;
  text-align: right;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
  border-right: 1px solid var(--border);
  user-select: none;
  min-width: 40px;
}
.line-numbers span { padding: 0 4px; }
.code-content {
  padding: 16px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre;
  flex: 1;
}
</style>
