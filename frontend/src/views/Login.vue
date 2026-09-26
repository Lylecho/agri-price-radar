<script setup>
// 登录页 —— 应用设计令牌（白画布 + 翡翠绿唯一实心 CTA）
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import AppButton from '@/components/ui/AppButton.vue'
import AppCard from '@/components/ui/AppCard.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  errorMsg.value = ''
  if (!form.username || !form.password) {
    errorMsg.value = '请输入用户名与密码'
    return
  }
  loading.value = true
  try {
    const data = await userStore.login({ username: form.username, password: form.password })
    ElMessage.success(`欢迎, ${data.nickname || data.username}`)
    router.push(data.mustChangePwd ? '/change-password' : (route.query.redirect || '/dashboard'))
  } catch (e) {
    errorMsg.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-box">
      <div class="login-head">
        <span class="brand-dot"></span>
        <h1 class="t-display-md">菜价雷达</h1>
        <p class="t-body-md muted">农产品价格监测与短期预测系统</p>
      </div>

      <AppCard variant="light" shadow>
        <form class="form" @submit.prevent="onSubmit">
          <label class="field">
            <span class="t-caption">用户名</span>
            <el-input v-model="form.username" placeholder="请输入用户名" size="large" clearable />
          </label>
          <label class="field">
            <span class="t-caption">密码</span>
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              show-password
              @keyup.enter="onSubmit"
            />
          </label>
          <p v-if="errorMsg" class="error t-caption">{{ errorMsg }}</p>
          <AppButton type="button" variant="primary" :disabled="loading" @click="onSubmit">
            {{ loading ? '登录中…' : '登录' }}
          </AppButton>
          <p class="t-micro hint">开发环境预置账号：admin / admin123（超级管理员）</p>
        </form>
      </AppCard>

      <p class="t-micro foot">预测结果仅供参考, 不构成任何买卖建议</p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--apr-canvas);
}

.login-box {
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: var(--apr-space-lg);
}

.login-head {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--apr-space-xs);
}

.login-head h1 {
  margin: var(--apr-space-sm) 0 0;
}

.brand-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--apr-primary);
}

.muted {
  color: var(--apr-ink-mute);
  margin: 0;
}

.form {
  display: flex;
  flex-direction: column;
  gap: var(--apr-space-lg);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--apr-space-xs);
}

.error {
  color: var(--apr-accent-tomato);
  margin: 0;
}

.hint {
  margin: 0;
  text-align: center;
}

.foot {
  text-align: center;
  margin: 0;
}
</style>
