<template>
  <div class="app">
    <nav class="navbar">
      <router-link to="/" class="logo">📜 novel2script</router-link>
      <span class="subtitle">中文小说到 LRM 脚本转换</span>
    </nav>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}
.logo {
  font-size: 20px;
  font-weight: 700;
  color: var(--primary);
  text-decoration: none;
}
.subtitle {
  color: var(--text-muted);
  font-size: 13px;
}
.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}
</style>
