<script setup>
import { onMounted, reactive, ref } from 'vue'
import { fetchOpLogs } from '@/api/oplog'
import AppCard from '@/components/ui/AppCard.vue'
import AppButton from '@/components/ui/AppButton.vue'

const filters = reactive({ username: '', action: '' })
const page = ref(1)
const size = ref(10)
const data = ref({ records: [], total: 0 })
const loading = ref(false)
const error = ref('')
const actions = { LOGIN: '登录', CHANGE_PASSWORD: '修改密码', UPDATE_ALERT_RULE: '修改预警规则', TRIGGER_COLLECT: '采集请求' }
let sequence = 0
async function load(reset = false) {
  if (reset) page.value = 1
  const current = ++sequence
  loading.value = true
  error.value = ''
  try {
    const result = await fetchOpLogs({ page: page.value, size: size.value, ...filters })
    if (current === sequence) data.value = result
  } catch (e) {
    if (current === sequence) {
      data.value = { records: [], total: 0 }
      error.value = e.message || '审计记录加载失败'
    }
  } finally {
    if (current === sequence) loading.value = false
  }
}
function reset() { filters.username = ''; filters.action = ''; load(true) }
onMounted(() => load())
</script>

<template>
  <AppCard variant="light" v-loading="loading">
    <h2 class="t-heading-lg">操作审计</h2>
    <p class="t-caption">查看登录、改密、预警规则修改和采集请求记录。采集请求仅记录受理结果，执行结果请查看采集监控。</p>
    <form class="filters" @submit.prevent="load(true)">
      <el-input v-model="filters.username" maxlength="32" placeholder="用户名（精确匹配）" aria-label="用户名筛选" clearable />
      <el-select v-model="filters.action" placeholder="全部动作" aria-label="动作筛选" clearable>
        <el-option v-for="(label, value) in actions" :key="value" :label="label" :value="value" />
      </el-select>
      <AppButton type="submit" :disabled="loading">查询</AppButton>
      <AppButton type="button" variant="outline" @click="reset">重置</AppButton>
    </form>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <el-table :data="data.records" empty-text="暂无符合条件的审计记录">
      <el-table-column prop="username" label="操作人" min-width="130" show-overflow-tooltip />
      <el-table-column label="动作" min-width="130"><template #default="{ row }">{{ actions[row.action] || row.action }}</template></el-table-column>
      <el-table-column prop="target" label="目标对象" min-width="130" show-overflow-tooltip />
      <el-table-column label="结果" width="90"><template #default="{ row }"><el-tag :type="row.result === 'SUCCESS' ? 'success' : 'danger'">{{ row.result === 'SUCCESS' ? '成功' : '失败' }}</el-tag></template></el-table-column>
      <el-table-column prop="detail" label="摘要" min-width="220" show-overflow-tooltip />
      <el-table-column prop="ip" label="来源 IP" min-width="130" />
      <el-table-column prop="createdAt" label="时间（上海）" min-width="185" />
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" :page-size="size" :total="data.total" layout="prev, pager, next, total" @current-change="load(false)" />
  </AppCard>
</template>

<style scoped>
h2 { margin: 0; }
.filters { display: flex; gap: var(--apr-space-sm); flex-wrap: wrap; margin: var(--apr-space-lg) 0; }
.filters .el-input, .filters .el-select { width: 220px; }
.pager { margin-top: var(--apr-space-lg); justify-content: flex-end; }
</style>
