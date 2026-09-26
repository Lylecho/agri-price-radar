<script setup>
// 基础布局: 侧边栏(按角色渲染菜单) + 顶栏(用户/角色/退出) + 路由出口
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import AppButton from '@/components/ui/AppButton.vue'
import AppPill from '@/components/ui/AppPill.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 菜单项（预警配置仅 ADMIN 可见）
const menus = computed(() => {
  const list = [
    { path: '/dashboard', label: '数据看板', admin: false },
    { path: '/collect', label: '采集监控', admin: false },
    { path: '/categories', label: '品类管理', admin: false },
    { path: '/oplog', label: '操作审计', admin: true },
    { path: '/alert', label: '预警配置', admin: true },
    { path: '/style-guide', label: '设计规范', admin: false },
    { path: '/change-password', label: '修改密码', admin: false },
  ]
  return list.filter((m) => !m.admin || userStore.isAdmin)
})

onMounted(async () => {
  // 刷新页面后补齐用户信息（令牌有效则静默成功）
  if (userStore.isLoggedIn && !userStore.username) {
    try {
      await userStore.loadProfile()
    } catch {
      userStore.logout()
      router.push('/login')
    }
  }
})

function logout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-dot"></span>
        <span class="t-heading-md">菜价雷达</span>
      </div>
      <nav class="menu">
        <RouterLink
          v-for="m in menus"
          :key="m.path"
          :to="m.path"
          class="menu-item t-body-md"
          :class="{ active: route.path === m.path }"
        >
          {{ m.label }}
        </RouterLink>
      </nav>
      <div class="sidebar-foot t-micro">
        农产品价格监测与短期预测<br />预测结果仅供参考
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="t-heading-md">{{ route.meta.title?.split(' · ')[0] || '菜价雷达' }}</div>
        <div class="topbar-right">
          <AppPill variant="soft">{{ userStore.roleLabel }}</AppPill>
          <span class="t-body-md">{{ userStore.nickname || userStore.username }}</span>
          <AppButton variant="outline" @click="logout">退出登录</AppButton>
        </div>
      </header>
      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
  background: var(--apr-canvas-soft);
}

.sidebar {
  width: 220px;
  flex: 0 0 220px;
  background: var(--apr-canvas);
  border-right: 1px solid var(--apr-hairline-cool);
  display: flex;
  flex-direction: column;
  padding: var(--apr-space-lg);
  gap: var(--apr-space-lg);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--apr-space-sm);
}

.brand-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--apr-primary);
}

.menu {
  display: flex;
  flex-direction: column;
  gap: var(--apr-space-xs);
  flex: 1;
}

.menu-item {
  padding: 10px var(--apr-space-md);
  border-radius: var(--apr-radius-sm);
  color: var(--apr-ink-secondary);
}

.menu-item:hover {
  background: var(--apr-canvas-soft);
}

.menu-item.active {
  background: var(--apr-primary-light, #ecfaf4);
  color: var(--apr-ink);
  font-weight: 500;
}

.sidebar-foot {
  border-top: 1px solid var(--apr-hairline-cool);
  padding-top: var(--apr-space-md);
  line-height: 1.6;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.topbar {
  height: 64px;
  background: var(--apr-canvas);
  border-bottom: 1px solid var(--apr-hairline-cool);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--apr-space-xl);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--apr-space-md);
}

.content {
  padding: var(--apr-space-xl);
}

@media (max-width: 767px) {
  .sidebar {
    display: none;
  }
}
</style>
