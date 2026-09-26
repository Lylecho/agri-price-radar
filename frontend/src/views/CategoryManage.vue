<script setup>
import { onMounted, ref } from 'vue'
import { fetchCategories } from '@/api/price'
import { fetchCategoryStats } from '@/api/collect'
import AppCard from '@/components/ui/AppCard.vue'
import AppButton from '@/components/ui/AppButton.vue'

const rows = ref([])
const loading = ref(false)
const error = ref('')
async function load() {
  loading.value = true
  error.value = ''
  try {
    const categories = await fetchCategories()
    rows.value = await Promise.all(categories.map(async c => ({ ...c, ...await fetchCategoryStats(c.category) })))
  } catch (e) {
    rows.value = []
    error.value = e.message || '品类数据加载失败'
  } finally { loading.value = false }
}
function status(row) {
  if (!row.cnt || !row.unit) return '暂无可核查数据'
  return row.unit !== '斤' || row.nonStandardUnitCount > 0 || row.suspectPriceCount > 0 ? '需复核' : '单位检查通过'
}
onMounted(load)
</script>

<template>
  <div class="categories" v-loading="loading">
    <AppCard variant="light">
      <div class="head"><h2 class="t-heading-lg">品类管理</h2><AppButton type="button" variant="outline" :disabled="loading" @click="load">刷新</AppButton></div>
      <p class="t-caption">五个监测品类与代表品名的只读目录。数据量和覆盖日期来自已入库明细。</p>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <el-table :data="rows" empty-text="暂无品类数据">
        <el-table-column prop="category" label="监测品类" min-width="100" />
        <el-table-column prop="prodName" label="代表品名" min-width="110" />
        <el-table-column prop="cnt" label="入库条数" min-width="110" />
        <el-table-column prop="minDate" label="最早日期" min-width="120" />
        <el-table-column prop="maxDate" label="最新日期" min-width="120" />
        <el-table-column prop="unit" label="主导单位" min-width="100" />
        <el-table-column label="单位治理状态" min-width="160"><template #default="{ row }"><el-tag :type="status(row) === '单位检查通过' ? 'success' : 'warning'">{{ status(row) }}</el-tag></template></el-table-column>
        <el-table-column prop="nonStandardUnitCount" label="非斤/缺失单位" min-width="130" />
        <el-table-column prop="suspectPriceCount" label="疑似价格错标" min-width="120" />
      </el-table>
    </AppCard>
    <AppCard variant="soft">
      <h3 class="t-heading-md">统计与核查口径</h3>
      <p class="t-body-md">入库条数及日期跨度包含代表品名的全部计价单位；主导单位按明细数量确定。不同计价单位不应直接放在同一价格轴比较。</p>
      <p class="t-body-md">当前检查非斤或缺失单位，以及散鸡蛋“斤”价超过 15 元的疑似错标。检查通过仅表示未命中这些规则；本页不自动隔离或修改数据。</p>
    </AppCard>
  </div>
</template>

<style scoped>
.categories { display: flex; flex-direction: column; gap: var(--apr-space-lg); }
.head { display: flex; align-items: center; justify-content: space-between; }
h2, h3 { margin: 0; }
p { line-height: 1.7; }
</style>
