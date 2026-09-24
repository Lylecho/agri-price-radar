import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录 · 菜价雷达', public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/BasicLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '数据看板 · 菜价雷达', icon: 'DataLine' },
      },
      {
        path: 'collect',
        name: 'collect',
        component: () => import('@/views/CollectMonitor.vue'),
        meta: { title: '采集监控 · 菜价雷达', icon: 'Monitor' },
      },
      {
        path: 'alert',
        name: 'alert',
        component: () => import('@/views/AlertConfig.vue'),
        meta: { title: '预警配置 · 菜价雷达', icon: 'Bell' },
      },
      {
        path: 'style-guide',
        name: 'style-guide',
        component: () => import('@/views/StyleGuide.vue'),
        meta: { title: '设计规范 · 菜价雷达', icon: 'Brush' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 登录守卫: 非公开页面必须已登录
router.beforeEach((to) => {
  const userStore = useUserStore()
  if (!to.meta.public && !userStore.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && userStore.isLoggedIn) {
    return { path: '/dashboard' }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title || '菜价雷达'
})

export default router
