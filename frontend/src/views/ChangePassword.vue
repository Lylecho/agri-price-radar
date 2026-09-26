<script setup>
// 首次登录强制改密，普通用户也可从菜单主动修改密码
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import AppCard from '@/components/ui/AppCard.vue'
import AppButton from '@/components/ui/AppButton.vue'

const router = useRouter()
const userStore = useUserStore()
const form = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })
const loading = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  errorMsg.value = ''
  if (!form.oldPassword || !form.newPassword || !form.confirmPassword) {
    errorMsg.value = '请填写全部密码项'
    return
  }
  if (form.newPassword.length < 8) {
    errorMsg.value = '新密码至少需要 8 个字符'
    return
  }
  if (form.newPassword !== form.confirmPassword) {
    errorMsg.value = '两次输入的新密码不一致'
    return
  }
  loading.value = true
  try {
    await changePassword({ oldPassword: form.oldPassword, newPassword: form.newPassword })
    await userStore.loadProfile()
    form.oldPassword = ''
    form.newPassword = ''
    form.confirmPassword = ''
    ElMessage.success('密码修改成功')
    router.replace('/dashboard')
  } catch (e) {
    errorMsg.value = e.message || '修改失败'
  } finally {
    loading.value = false
  }
}

function logout() {
  userStore.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="page">
    <div class="box">
      <div>
        <h1 class="t-display-md">修改密码</h1>
        <p class="t-body-md muted">
          {{ userStore.mustChangePwd ? '首次登录须先修改预置密码，完成后才能使用系统。' : '修改当前账号密码。' }}
        </p>
      </div>
      <AppCard variant="light" shadow>
        <form class="form" @submit.prevent="onSubmit">
          <label class="field">
            <span class="t-caption">当前密码</span>
            <el-input v-model="form.oldPassword" type="password" show-password autocomplete="current-password" />
          </label>
          <label class="field">
            <span class="t-caption">新密码（至少 8 个字符）</span>
            <el-input v-model="form.newPassword" type="password" show-password autocomplete="new-password" />
          </label>
          <label class="field">
            <span class="t-caption">确认新密码</span>
            <el-input v-model="form.confirmPassword" type="password" show-password autocomplete="new-password" />
          </label>
          <p v-if="errorMsg" class="error t-caption">{{ errorMsg }}</p>
          <div class="actions">
            <AppButton type="button" variant="primary" :disabled="loading" @click="onSubmit">
              {{ loading ? '提交中…' : '确认修改' }}
            </AppButton>
            <AppButton type="button" variant="outline" @click="logout">退出登录</AppButton>
          </div>
        </form>
      </AppCard>
      <p class="t-micro muted">菜价雷达 · 预测结果仅供参考</p>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--apr-canvas);
}
.box {
  width: min(440px, calc(100vw - 32px));
  display: flex;
  flex-direction: column;
  gap: var(--apr-space-lg);
}
.box h1 { margin: 0; }
.muted { color: var(--apr-ink-mute); margin: var(--apr-space-xs) 0 0; }
.form, .field { display: flex; flex-direction: column; gap: var(--apr-space-sm); }
.form { gap: var(--apr-space-lg); }
.actions { display: flex; gap: var(--apr-space-sm); }
.error { color: var(--apr-accent-tomato); margin: 0; }
</style>
