<template>
  <div class="screenplay">
    <!-- 顶部信息 -->
    <header class="sp-header">
      <h1 class="sp-title">{{ data.title || '未命名剧本' }}</h1>
      <div class="sp-meta">
        <span v-if="data.author">原著：{{ data.author }}</span>
        <span v-if="data.genre">类型：{{ data.genre }}</span>
      </div>
      <div v-if="charList.length" class="sp-characters">
        <span class="sp-char-label">角色：</span>
        <span v-for="(c, i) in charList" :key="i" class="sp-char-tag">{{ c.name }}</span>
      </div>
    </header>

    <!-- 章节 -->
    <div v-for="ch in chapters" :key="ch.chapter_number" class="sp-chapter">
      <div class="sp-chapter-header">
        <span class="sp-chapter-num">第 {{ ch.chapter_number }} 章</span>
        <span v-if="ch.title || ch.chapter_title" class="sp-chapter-title">{{ ch.title || ch.chapter_title }}</span>
      </div>

      <!-- 场景 -->
      <div
        v-for="scene in (ch.scenes || [])"
        :key="scene.scene_number"
        class="sp-scene"
        :class="sceneClass(scene.int_ext)"
      >
        <div class="sp-scene-header">
          <span class="sp-heading">{{ scene.heading || buildHeading(scene) }}</span>
          <span v-if="scene.time_of_day" class="sp-time">{{ scene.time_of_day }}</span>
        </div>
        <div v-if="scene.characters && scene.characters.length" class="sp-scene-chars">
          <span v-for="c in scene.characters" :key="c" class="sp-scene-char">{{ c }}</span>
        </div>
        <p v-if="scene.summary" class="sp-summary">{{ scene.summary }}</p>

        <!-- 内容 -->
        <div class="sp-content">
          <template v-for="(item, idx) in (scene.content || [])" :key="idx">
            <!-- 动作 -->
            <p v-if="item.type === 'action'" class="sp-action">{{ item.text }}</p>
            <!-- 对白 -->
            <div v-else-if="item.type === 'dialogue'" class="sp-dialogue">
              <span class="sp-char-name">{{ item.character }}</span>
              <span v-if="item.parenthetical" class="sp-paren">（{{ item.parenthetical }}）</span>
              <p class="sp-line">{{ item.text }}</p>
            </div>
            <!-- 兜底 -->
            <p v-else class="sp-action">{{ item.text || JSON.stringify(item) }}</p>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, required: true }
})

const chapters = computed(() => props.data.chapters || [])

const charList = computed(() => {
  const chars = props.data.characters
  if (!chars) return []
  if (Array.isArray(chars)) {
    return chars.map(c => typeof c === 'string' ? { name: c } : { name: c.name || c.姓名 || '', desc: c.description || c.简介 || '' })
  }
  // map 格式 { "角色名": "简介" }
  return Object.entries(chars).map(([name, desc]) => ({ name, desc }))
})

function sceneClass(intExt) {
  if (!intExt) return ''
  if (intExt.includes('外')) return 'sp-scene-ext'
  return 'sp-scene-int'
}

function buildHeading(scene) {
  const parts = []
  if (scene.int_ext) parts.push(scene.int_ext)
  if (scene.location) parts.push(scene.location)
  if (scene.time_of_day) parts.push('- ' + scene.time_of_day)
  return parts.join(' ') || '场景'
}
</script>

<style scoped>
.screenplay {
  font-family: "Noto Serif SC", "Source Han Serif SC", "Songti SC", Georgia, serif;
  line-height: 1.8; color: #1e293b; max-width: 720px;
}

/* 顶部 */
.sp-header {
  text-align: center; padding-bottom: 24px; margin-bottom: 32px;
  border-bottom: 2px solid #e2e8f0;
}
.sp-title { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
.sp-meta {
  display: flex; gap: 20px; justify-content: center;
  font-size: 14px; color: #64748b; margin-bottom: 12px;
}
.sp-characters {
  display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: center;
}
.sp-char-label { font-size: 13px; color: #64748b; }
.sp-char-tag {
  font-size: 12px; background: #eef2ff; color: #6366f1;
  padding: 2px 10px; border-radius: 999px; font-weight: 500;
}

/* 章节 */
.sp-chapter { margin-bottom: 40px; }
.sp-chapter-header {
  display: flex; align-items: baseline; gap: 12px;
  margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #e2e8f0;
}
.sp-chapter-num {
  font-size: 13px; font-weight: 600; color: #6366f1;
  background: #eef2ff; padding: 3px 12px; border-radius: 6px;
  white-space: nowrap;
}
.sp-chapter-title { font-size: 18px; font-weight: 600; }

/* 场景 */
.sp-scene {
  margin-bottom: 28px; padding: 20px 24px;
  border-radius: 10px; background: #fff;
  border: 1px solid #e2e8f0; border-left: 4px solid #cbd5e1;
}
.sp-scene-int { border-left-color: #6366f1; }
.sp-scene-ext { border-left-color: #10b981; }

.sp-scene-header {
  display: flex; align-items: center; gap: 10px; margin-bottom: 8px;
}
.sp-heading {
  font-size: 15px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.05em; color: #334155;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.sp-time {
  font-size: 12px; color: #64748b; background: #f1f5f9;
  padding: 2px 8px; border-radius: 4px;
}
.sp-scene-chars {
  display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px;
}
.sp-scene-char {
  font-size: 12px; background: #f1f5f9; color: #475569;
  padding: 2px 8px; border-radius: 4px;
}
.sp-summary {
  font-size: 13px; color: #64748b; font-style: italic;
  margin-bottom: 14px; padding-left: 12px;
  border-left: 2px solid #e2e8f0;
}

/* 内容 */
.sp-content { margin-top: 12px; }

/* 动作 */
.sp-action {
  font-size: 15px; color: #475569; line-height: 1.9;
  margin-bottom: 14px; text-indent: 2em;
}

/* 对白 */
.sp-dialogue {
  margin-bottom: 14px; padding: 12px 16px 12px 20px;
  background: #f8fafc; border-radius: 8px;
  border-left: 3px solid #6366f1;
}
.sp-char-name {
  font-size: 14px; font-weight: 700; color: #6366f1;
  text-transform: uppercase; letter-spacing: 0.04em;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.sp-paren {
  font-size: 13px; color: #94a3b8; margin-left: 6px;
}
.sp-line {
  font-size: 15px; color: #1e293b; line-height: 1.8;
  margin-top: 4px;
}
</style>
