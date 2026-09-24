// 路由 —— 本轮仅设计规范展示页(业务页面等后端接口就绪后再增)
import { createRouter, createWebHistory } from 'vue-router'
import StyleGuide from '@/views/StyleGuide.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/style-guide' },
    {
      path: '/style-guide',
      name: 'style-guide',
      component: StyleGuide,
      meta: { title: '设计规范 · 菜价雷达' },
    },
  ],
})

router.afterEach((to) => {
  document.title = to.meta.title || '菜价雷达'
})

export default router
