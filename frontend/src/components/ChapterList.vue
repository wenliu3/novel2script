<template>
  <div class="chapter-list">
    <h3>章节列表 <span class="count">({{ chapters.length }})</span></h3>
    <div class="list">
      <div
        v-for="ch in chapters"
        :key="ch.number"
        class="chapter-item"
        @click="toggle(ch.number)"
      >
        <div class="ch-header">
          <span class="ch-num">#{{ ch.number }}</span>
          <span class="ch-title">{{ ch.title || '无标题' }}</span>
          <span class="ch-words">{{ ch.word_count?.toLocaleString() || '?' }} 字</span>
          <span class="arrow">{{ expanded.has(ch.number) ? '▼' : '▶' }}</span>
        </div>
        <div v-if="expanded.has(ch.number)" class="ch-preview">
          {{ ch.raw_text?.slice(0, 200) || '无内容' }}...
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ chapters: Array })

const expanded = ref(new Set())

function toggle(num) {
  if (expanded.value.has(num)) {
    expanded.value.delete(num)
  } else {
    expanded.value.add(num)
  }
}
</script>

<style scoped>
h3 { font-size: 16px; margin-bottom: 12px; }
.count { color: var(--text-muted); font-weight: normal; }
.chapter-item {
  border-bottom: 1px solid var(--border);
  padding: 10px 0;
  cursor: pointer;
}
.chapter-item:hover { background: var(--bg-hover); margin: 0 -8px; padding: 10px 8px; border-radius: 4px; }
.ch-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}
.ch-num { color: var(--text-muted); font-size: 12px; min-width: 32px; }
.ch-title { flex: 1; }
.ch-words { color: var(--text-muted); font-size: 12px; }
.arrow { color: var(--text-muted); font-size: 12px; }
.ch-preview {
  margin-top: 8px;
  padding: 8px;
  background: var(--bg);
  border-radius: 4px;
  font-size: 13px;
  color: var(--text-muted);
  white-space: pre-wrap;
}
</style>
