<template>
  <div class="convert-section">
    <button class="btn-primary btn-lg" @click="showModal = true">
      🎬 开始转换
    </button>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal card">
        <h2>转换参数</h2>

        <div class="form-group">
          <label>章节范围</label>
          <div class="radio-group">
            <label><input type="radio" v-model="mode" value="all" /> 全部 ({{ chapterCount }} 章)</label>
            <label><input type="radio" v-model="mode" value="range" /> 指定范围</label>
          </div>
          <div v-if="mode === 'range'" class="range-inputs">
            <input v-model.number="startCh" type="number" min="1" :max="chapterCount" class="input-sm" />
            <span>~</span>
            <input v-model.number="endCh" type="number" min="1" :max="chapterCount" class="input-sm" />
          </div>
        </div>

        <div class="actions">
          <button class="btn-ghost" @click="showModal = false">取消</button>
          <button class="btn-primary" :disabled="converting" @click="handleConvert">
            {{ converting ? '转换中...' : '确认转换' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { startConvert } from '../api'

const props = defineProps({
  novelName: String,
  chapterCount: Number,
})

const emit = defineEmits(['started'])

const showModal = ref(false)
const mode = ref('all')
const startCh = ref(1)
const endCh = ref(props.chapterCount || 1)
const converting = ref(false)

async function handleConvert() {
  converting.value = true
  try {
    let chapters = null
    if (mode.value === 'range') {
      chapters = []
      for (let i = startCh.value; i <= endCh.value; i++) chapters.push(i)
    }
    const result = await startConvert(props.novelName, { chapters })
    emit('started', result.task_id || 'default')
    showModal.value = false
  } catch (e) {
    alert('转换失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    converting.value = false
  }
}
</script>

<style scoped>
.btn-lg { padding: 12px 32px; font-size: 16px; }
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal { width: 400px; }
.modal h2 { margin-bottom: 16px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; color: var(--text-muted); margin-bottom: 4px; }
.radio-group { display: flex; flex-direction: column; gap: 6px; }
.radio-group label { color: var(--text); cursor: pointer; }
.range-inputs { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.input-sm {
  width: 80px;
  padding: 6px 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 14px;
}
.actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
</style>
