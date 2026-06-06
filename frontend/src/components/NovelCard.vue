<template>
  <div class="novel-card card" @click="$emit('click')">
    <div class="card-header">
      <h3>{{ novel.name }}</h3>
      <button class="btn-ghost btn-sm" @click.stop="$emit('delete')">删除</button>
    </div>
    <div class="card-stats">
      <span>{{ novel.chapters }} 章</span>
      <span v-if="novel.total_chars">{{ novel.total_chars.toLocaleString() }} 字</span>
    </div>
    <div class="card-tags">
      <span v-if="novel.has_character" class="badge badge-green">角色文件 ✓</span>
      <span v-if="novel.has_overview" class="badge badge-green">概览 ✓</span>
    </div>
  </div>
</template>

<script setup>
defineProps({ novel: Object })
defineEmits(['click', 'delete'])
</script>

<style scoped>
.novel-card { cursor: pointer; }
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.card-header h3 { font-size: 16px; }
.card-stats {
  display: flex;
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
  margin-bottom: 8px;
}
.card-tags { display: flex; gap: 6px; }
.btn-sm { padding: 4px 8px; font-size: 12px; }
</style>
