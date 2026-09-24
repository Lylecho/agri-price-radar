<script setup>
// 采集监控 —— 任务日志分页 + 各品类数据量与跨度 + 手动触发采集
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchCategoryStats, fetchCollectLogs, triggerCollect } from '@/api/collect'
import { fetchCategories } from '@/api/price'
import AppCard from '@/components/ui/AppCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppPill from '@/components/ui/AppPill.vue'

const loading = ref(false)
const logs = ref({ records: [], total: 0 })
const page = ref(1)
const size = ref(10)
const stats = ref([])
const triggering = ref(false)

async function loadLogs() {
  const data = await fetchCollectLogs(page.value, size.value)
  logs.value = data
}

async function loadStats() {
  const cats = await fetchCategories()
  stats.value = await Promise.all(
    cats.map(async (c) => {
      try {
        const s = await fetchCategoryStats(c.category)
        return { category: c.category, prodName: c.prodName, ...s }
      } catch {
        return { category: c.category, prodName: c.prodName, cnt: null }
      }
    }),
  )
}

async function refresh() {
  loading.value = true
  try {
    await Promise.all([loadLogs(), loadStats()])
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function onTrigger() {
  triggering.value = true
  try {
    const res = await triggerCollect()
    ElMessage.success(res?.message || '已提交采集任务, 请稍后刷新查看日志')
    setTimeout(refresh, 3000)
  } catch (e) {
    ElMessage.error(e.message || '触发失败')
  } finally {
    triggering.value = false
  }
}

function onPageChange(p) {
  page.value = p
  loadLogs()
}

function statusTag(status) {
  return status === 'SUCCESS' ? 'green' : 'soft'
}

onMounted(refresh)
</script>

<template>
  <div v-loading="loading" class="monitor">
    <AppCard variant="light">
      <div class="head">
        <div>
          <h3 class="t-heading-lg">数据量概览</h3>
          <p class="t-caption">各品类入库条数与时间跨度（只读快照）</p>
        </div>
        <AppButton variant="primary" :disabled="triggering" @click="onTrigger">
          {{ triggering ? '提交中…' : '手动触发采集' }}
        </AppButton>
      </div>
      <el-table :data="stats" size="small" style="width: 100%">
        <el-table-column prop="category" label="品类" width="110" />
        <el-table-column prop="prodName" label="代表品名" width="120" />
        <el-table-column prop="cnt" label="入库条数" width="120" />
        <el-table-column prop="minDate" label="最早日期" width="140" />
        <el-table-column prop="maxDate" label="最新日期" width="140" />
      </el-table>
    </AppCard>

    <AppCard variant="light">
      <h3 class="t-heading-lg">任务日志</h3>
      <p class="t-caption">定时采集(08/14/20点)与预计算(21点)的执行记录</p>
      <el-table :data="logs.records" size="small" style="width: 100%">
        <el-table-column prop="job" label="任务" width="110" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <AppPill :variant="statusTag(row.status)">{{ row.status }}</AppPill>
          </template>
        </el-table-column>
        <el-table-column prop="rowsWritten" label="写入行数" width="100" />
        <el-table-column prop="startedAt" label="开始时间" width="180" />
        <el-table-column prop="finishedAt" label="结束时间" width="180" />
        <el-table-column prop="detail" label="摘要" show-overflow-tooltip />
      </el-table>
      <div class="pager">
        <el-pagination
          layout="prev, pager, next, total"
          :total="logs.total"
          :current-page="page"
          :page-size="size"
          @current-change="onPageChange"
        />
      </div>
    </AppCard>
  </div>
</template>

<style scoped>
.monitor {
  display: flex;
  flex-direction: column;
  gap: var(--apr-space-lg);
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--apr-space-md);
}

.head h3 {
  margin: 0;
}

.head p {
  margin: var(--apr-space-xxs) 0 0;
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
