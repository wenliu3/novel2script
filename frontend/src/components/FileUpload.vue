<template>
  <div class="upload-overlay" @click.self="$emit('close')">
    <div class="upload-modal card">
      <h2>上传小说</h2>

      <div class="form-group">
        <label>小说名称</label>
        <input v-model="novelName" placeholder="如：诡秘之主" class="input" />
      </div>

      <div
        class="drop-zone"
        :class="{ dragover }"
        @dragover.prevent="dragover = true"
        @dragleave="dragover = false"
        @drop.prevent="handleDrop"
        @click="fileInput.click()"
      >
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".txt"
          hidden
          @change="handleFileSelect"
        />
        <div v-if="files.length === 0">
          <p>📄 拖拽 .txt 文件到这里，或点击选择</p>
          <p class="hint">支持多个文件，每个文件为一章</p>
        </div>
        <div v-else class="file-list">
          <div v-for="(f, i) in files" :key="i" class="file-item">
            <span>{{ f.name }}</span>
            <button class="btn-ghost btn-sm" @click.stop="removeFile(i)">×</button>
          </div>
        </div>
      </div>

      <div class="actions">
        <button class="btn-ghost" @click="$emit('close')">取消</button>
        <button
          class="btn-primary"
          :disabled="!novelName || files.length === 0 || uploading"
          @click="handleUpload"
        >
          {{ uploading ? '上传中...' : `上传 ${files.length} 个文件` }}
        </button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { uploadNovelFiles } from '../api'

const emit = defineEmits(['close', 'uploaded'])

const novelName = ref('')
const files = ref([])
const dragover = ref(false)
const uploading = ref(false)
const error = ref('')
const fileInput = ref(null)

function handleDrop(e) {
  dragover.value = false
  const dropped = [...e.dataTransfer.files].filter(f => f.name.endsWith('.txt'))
  files.value.push(...dropped)
}

function handleFileSelect(e) {
  files.value.push(...[...e.target.files])
}

function removeFile(index) {
  files.value.splice(index, 1)
}

async function handleUpload() {
  if (!novelName.value || files.value.length === 0) return
  uploading.value = true
  error.value = ''
  try {
    await uploadNovelFiles(novelName.value, files.value)
    emit('uploaded')
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.upload-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.upload-modal {
  width: 500px;
  max-width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
}
.upload-modal h2 { margin-bottom: 16px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; color: var(--text-muted); margin-bottom: 4px; }
.input {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 14px;
}
.input:focus { outline: none; border-color: var(--primary); }
.drop-zone {
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
  margin-bottom: 16px;
}
.drop-zone.dragover { border-color: var(--primary); }
.drop-zone .hint { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.file-list { text-align: left; }
.file-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
}
.btn-sm { padding: 2px 6px; font-size: 11px; }
.actions { display: flex; justify-content: flex-end; gap: 8px; }
.error { color: var(--danger); font-size: 13px; margin-top: 8px; }
</style>
