<template>
  <div class="home">
    <div class="header">
      <h1>小说列表</h1>
      <button class="btn-primary" @click="showUpload = true">+ 上传小说</button>
    </div>

    <div v-if="loading" class="empty-state">加载中...</div>

    <div v-else-if="novels.length === 0" class="empty-state">
      <div class="icon">📚</div>
      <p>还没有上传任何小说</p>
      <p>点击右上角「上传小说」开始</p>
    </div>

    <div v-else class="grid">
      <NovelCard
        v-for="novel in novels"
        :key="novel.name"
        :novel="novel"
        @click="$router.push(`/novel/${novel.name}`)"
        @delete="handleDelete(novel.name)"
      />
    </div>

    <FileUpload
      v-if="showUpload"
      @close="showUpload = false"
      @uploaded="loadNovels"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchNovels, deleteNovel } from '../api'
import NovelCard from '../components/NovelCard.vue'
import FileUpload from '../components/FileUpload.vue'

const novels = ref([])
const loading = ref(true)
const showUpload = ref(false)

async function loadNovels() {
  loading.value = true
  try {
    novels.value = await fetchNovels()
  } catch (e) {
    console.error('加载失败:', e)
  } finally {
    loading.value = false
  }
}

async function handleDelete(name) {
  if (!confirm(`确定删除「${name}」？`)) return
  await deleteNovel(name)
  await loadNovels()
}

onMounted(loadNovels)
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.header h1 { font-size: 24px; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
</style>
