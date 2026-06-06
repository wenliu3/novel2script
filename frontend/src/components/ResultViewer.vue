<template>
  <div class="result-viewer">
    <div class="viewer-header">
      <span class="filename mono">{{ fileName }}</span>
      <div class="actions">
        <button class="btn-ghost btn-sm" @click="$emit('download')">下载</button>
      </div>
    </div>
    <div v-if="isYaml" class="code-container">
      <div class="line-numbers">
        <span v-for="n in lineCount" :key="n">{{ n }}</span>
      </div>
      <pre class="code-content mono">{{ content }}</pre>
    </div>
    <div v-else class="markdown-container">
      <pre class="code-content mono">{{ content }}</pre>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  fileName: String,
  content: String,
})

defineEmits(['download'])

const isYaml = computed(() =>
  props.fileName?.endsWith('.yaml') || props.fileName?.endsWith('.yml')
)

const lineCount = computed(() =>
  (props.content || '').split('\n').length
)
</script>

<style scoped>
.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}
.filename { font-size: 13px; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.code-container {
  display: flex;
  background: #0d1117;
  min-height: 400px;
  max-height: 700px;
  overflow: auto;
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
.markdown-container {
  background: #0d1117;
  padding: 16px;
  min-height: 400px;
}
</style>
