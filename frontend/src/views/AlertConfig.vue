<script setup>
// 预警配置 —— 规则阈值维护(仅 ADMIN 可改) + 预警记录列表
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'
import { useUserStore } from '@/stores/user'
import AppCard from '@/components/ui/AppCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppPill from '@/components/ui/AppPill.vue'

const userStore = useUserStore()
const canEdit = computed(() => userStore.isAdmin)

const loading = ref(false)
const rules = ref([])
const records = ref({ records: [], total: 0 })
const page = ref(1)
const size = ref(10)
const editing = ref({})   // { [ruleId]: threshold }

async function loadRules() {
  rules.value = await request.get('/api/alert/rules')
  editing.value = Object.fromEntries(rules.value.map((r) => [r.id, Number(r.threshold)]))
}

async function loadRecords() {
  const data = await request.get('/api/alert/records', { params: { page: page.value, size: size.value } })
  records.value = data
}

async function refresh() {
  loading.value = true
  try {
    await Promise.all([loadRules(), loadRecords()])
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function saveRule(rule) {
  try {
    await request.put(`/api/alert/rules/${rule.id}`, {
      threshold: Number(editing.value[rule.id]),
      enabled: rule.enabled,
      remark: rule.remark,
    })
    ElMessage.success(`${rule.category} 阈值已更新`)
    await loadRules()
  } catch (e) {
    ElMessage.error(e.message || '更新失败')
  }
}

async function toggleEnabled(rule) {
  try {
    await request.put(`/api/alert/rules/${rule.id}`, {
      threshold: Number(editing.value[rule.id] ?? rule.threshold),
      enabled: rule.enabled === 1 ? 0 : 1,
      remark: rule.remark,
    })
    ElMessage.success('状态已更新')
    await loadRules()
  } catch (e) {
    ElMessage.error(e.message || '更新失败')
  }
}

function onPageChange(p) {
  page.value = p
  loadRecords()
}

function pctColor(pct) {
  const v = Number(pct)
  if (Number.isNaN(v)) return 'var(--apr-ink-mute)'
  return v > 0 ? '#d94e41' : v < 0 ? '#3aa372' : 'var(--apr-ink-mute)'
}

onMounted(refresh)
</script>

<template>
  <div v-loading="loading" class="alert-page">
    <AppCard variant="light">
      <div class="head">
        <div>
          <h3 class="t-heading-lg">波动预警规则</h3>
          <p class="t-caption">
            阈值语义：日环比涨跌幅的绝对值 ≥ 阈值时触发（单位 %）。
            <span v-if="!canEdit">仅超级管理员可修改。</span>
          </p>
        </div>
      </div>
      <el-table :data="rules" size="small" style="width: 100%">
        <el-table-column prop="category" label="品类" width="110" />
        <el-table-column label="指标" width="140">
          <template #default="{ row }">
            <AppPill variant="soft">{{ row.metric === 'DOD_PCT' ? '日环比涨跌幅' : row.metric }}</AppPill>
          </template>
        </el-table-column>
        <el-table-column label="阈值(%)" width="180">
          <template #default="{ row }">
            <el-input-number
              v-model="editing[row.id]"
              :min="0.01"
              :max="100"
              :step="0.5"
              :precision="2"
              size="small"
              :disabled="!canEdit"
            />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <AppPill :variant="row.enabled === 1 ? 'green' : 'soft'">
              {{ row.enabled === 1 ? '启用' : '停用' }}
            </AppPill>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" show-overflow-tooltip />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <AppButton variant="link" :disabled="!canEdit" @click="saveRule(row)">保存阈值</AppButton>
            <AppButton variant="link" :disabled="!canEdit" @click="toggleEnabled(row)">
              {{ row.enabled === 1 ? '停用' : '启用' }}
            </AppButton>
          </template>
        </el-table-column>
      </el-table>
    </AppCard>

    <AppCard variant="light">
      <h3 class="t-heading-lg">预警记录</h3>
      <p class="t-caption">定时任务（每日 21:30）按上述阈值自动评估并留痕</p>
      <el-table :data="records.records" size="small" style="width: 100%">
        <el-table-column prop="tradeDate" label="交易日" width="130" />
        <el-table-column prop="category" label="品类" width="100" />
        <el-table-column label="涨跌幅" width="110">
          <template #default="{ row }">
            <span :style="{ color: pctColor(row.changePct) }">{{ row.changePct }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="latestPrice" label="当日均价" width="110" />
        <el-table-column prop="prevPrice" label="基准均价" width="110" />
        <el-table-column prop="threshold" label="阈值(%)" width="100" />
        <el-table-column prop="message" label="提示" show-overflow-tooltip />
      </el-table>
      <div class="pager">
        <el-pagination
          layout="prev, pager, next, total"
          :total="records.total"
          :current-page="page"
          :page-size="size"
          @current-change="onPageChange"
        />
      </div>
    </AppCard>
  </div>
</template>

<style scoped>
.alert-page {
  display: flex;
  flex-direction: column;
  gap: var(--apr-space-lg);
}

.head {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--apr-space-md);
}

h3 {
  margin: 0 0 var(--apr-space-xxs);
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--apr-space-md);
}
</style>
