<template>
  <div class="progress-panel card">
    <div class="progress-header">
      <span>转换进度</span>
      <span class="status" :class="statusClass">{{ statusText }}</span>
    </div>

    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: percent + '%' }"></div>
    </div>

    <div class="progress-info">
      <span>{{ currentMessage }}</span>
      <span>{{ percent }}%</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { fetchTaskStatus } from '../api'

const props = defineProps({ taskId: String })
const emit = defineEmits(['complete'])

const percent = ref(10)
const currentMessage = ref('任务排队中...')
const status = ref('pending')
let timer = null

const statusText = computed(() => {
  const map = { pending: '排队中', processing: '转换中', completed: '已完成', failed: '失败' }
  return map[status.value] || status.value
})
const statusClass = computed(() => {
  const map = { completed: 'badge-green', failed: 'badge-red' }
  return map[status.value] || ''
})

async function poll() {
  try {
    const data = await fetchTaskStatus(props.taskId)
    const taskStatus = data.status || 'pending'
    status.value = taskStatus

    // 根据后端返回的 status 映射进度
    if (taskStatus === 'pending') {
      percent.value = 10
      currentMessage.value = '任务排队中...'
    } else if (taskStatus === 'processing') {
      percent.value = 50
      currentMessage.value = '转换中，请稍候...'
    } else if (taskStatus === 'completed') {
      percent.value = 100
      currentMessage.value = '转换完成'
      emit('complete')
      clearInterval(timer)
    } else if (taskStatus === 'failed') {
      percent.value = 0
      currentMessage.value = data.message || '转换失败'
      clearInterval(timer)
    }
  } catch (e) {
    console.error('轮询失败:', e)
  }
}

onMounted(() => {
  timer = setInterval(poll, 2000)
  poll()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.progress-bar {
  height: 8px;
  background: var(--bg);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}
.progress-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 4px;
  transition: width 0.3s;
}
.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-muted);
}
</style>
