<template>
  <div class="novel-detail">
    <div class="top-bar">
      <router-link to="/">← 返回</router-link>
      <h1>{{ name }}</h1>
    </div>

    <div v-if="loading" class="empty-state">加载中...</div>

    <template v-else-if="detail">
      <!-- 信息面板 -->
      <div class="info-panel card">
        <div class="info-row">
          <span class="label">章节数</span>
          <span class="value">{{ detail.chapter_count }}</span>
        </div>
        <div class="info-row">
          <span class="label">总字数</span>
          <span class="value">{{ detail.total_chars?.toLocaleString() }}</span>
        </div>
        <div class="info-row">
          <span class="label">编码</span>
          <span class="value">{{ detail.encoding || 'UTF-8' }}</span>
        </div>
        <div class="info-row">
          <span class="label">角色文件</span>
          <span :class="detail.has_character ? 'badge badge-green' : 'badge badge-yellow'">
            {{ detail.has_character ? '已有' : '无' }}
          </span>
        </div>
      </div>

      <!-- 章节列表 -->
      <ChapterList :chapters="detail.chapters || []" />

      <!-- 操作栏 -->
      <div class="action-bar">
        <ConvertButton
          :novel-name="name"
          :chapter-count="detail.chapter_count"
          @started="handleConvertStarted"
        />
      </div>

      <!-- 进度 -->
      <TaskProgress v-if="taskId" :task-id="taskId" @complete="handleComplete" />
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchNovelDetail } from '../api'
import ChapterList from '../components/ChapterList.vue'
import ConvertButton from '../components/ConvertButton.vue'
import TaskProgress from '../components/TaskProgress.vue'

const route = useRoute()
const router = useRouter()
const name = route.params.name

const detail = ref(null)
const loading = ref(true)
const taskId = ref('')

async function loadDetail() {
  loading.value = true
  try {
    detail.value = await fetchNovelDetail(name)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handleConvertStarted(id) {
  taskId.value = id
}

function handleComplete() {
  taskId.value = ''
  router.push(`/result/${name}`)
}

onMounted(loadDetail)
</script>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.top-bar h1 { font-size: 22px; }
.info-panel {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.info-row { display: flex; flex-direction: column; gap: 4px; }
.info-row .label { color: var(--text-muted); font-size: 12px; }
.info-row .value { font-size: 18px; font-weight: 600; }
.action-bar {
  margin-top: 24px;
  text-align: center;
}
</style>
