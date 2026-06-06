import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('../views/Home.vue') },
  { path: '/novel/:name', name: 'NovelDetail', component: () => import('../views/NovelDetail.vue'), props: true },
  { path: '/result/:name', name: 'Result', component: () => import('../views/Result.vue'), props: true },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
