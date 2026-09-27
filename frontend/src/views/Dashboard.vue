<script setup>
// 数据看板 —— 五品类概览(红涨绿跌) + 近N天趋势 + 未来7天预测(含免责声明)
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchCategories, fetchChange, fetchTrend } from '@/api/price'
import { fetchPredict, fetchRealtimePredict } from '@/api/predict'
import AppButton from '@/components/ui/AppButton.vue'
import AppCard from '@/components/ui/AppCard.vue'
import AppPill from '@/components/ui/AppPill.vue'
import TrendChart from '@/components/charts/TrendChart.vue'
import PredictChart from '@/components/charts/PredictChart.vue'

const loading = ref(true)
const cards = ref([])          // [{ category, prodName, unit, latestDate, latestPrice, changePct }]
const selected = ref('')
const rangeDays = ref(90)
const trendPoints = ref([])
const predictData = ref(null)
const predictError = ref(false)
const detailLoading = ref(false)
const realtimeLoading = ref(false)
let detailSequence = 0

const rangeOptions = [
  { label: '近90天', value: 90 },
  { label: '近1年', value: 365 },
  { label: '近3年', value: 1095 },
]

const selectedCard = computed(() => cards.value.find((c) => c.category === selected.value) || null)

const trendSeries = computed(() => {
  if (!selected.value || !trendPoints.value.length) return []
  return [
    {
      name: `${selected.value}(${selectedCard.value?.unit || ''})`,
      data: trendPoints.value.map((p) => [p.tradeDate, Number(p.avgPrice)]),
    },
  ]
})

const predictHistory = computed(() => {
  // 预测图展示近90天历史 + 未来7天
  const recent = trendPoints.value.slice(-90)
  return recent.map((p) => [p.tradeDate, Number(p.avgPrice)])
})

const predictPoints = computed(() =>
  (predictData.value?.points || []).map((p) => [p.date, Number(p.yhat)]),
)

/** 红涨绿跌（中国惯例） */
function changeColor(pct) {
  if (pct == null) return 'var(--apr-ink-mute)'
  return pct > 0 ? '#d94e41' : pct < 0 ? '#3aa372' : 'var(--apr-ink-mute)'
}

function changeText(pct) {
  if (pct == null) return '—'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct}%`
}

async function loadCards() {
  const list = await fetchCategories()
  // 并发补齐环比（失败不阻塞整体展示）
  const withChange = await Promise.all(
    list.map(async (item) => {
      try {
        const chg = await fetchChange(item.category)
        return { ...item, changePct: chg.changePct }
      } catch {
        return { ...item, changePct: null }
      }
    }),
  )
  cards.value = withChange
  if (!selected.value && withChange.length) {
    selected.value = withChange[0].category
  }
}

async function loadDetail() {
  if (!selected.value) return
  const sequence = ++detailSequence
  realtimeLoading.value = false
  detailLoading.value = true
  predictData.value = null
  predictError.value = false
  const [trend, pred] = await Promise.allSettled([
    fetchTrend(selected.value, rangeDays.value),
    fetchPredict(selected.value),
  ])
  if (sequence !== detailSequence) return
  trendPoints.value = trend.status === 'fulfilled' ? trend.value : []
  predictData.value = pred.status === 'fulfilled' ? pred.value : null
  predictError.value = pred.status === 'rejected'
  detailLoading.value = false
}

async function refresh() {
  loading.value = true
  try {
    await loadCards()
    await loadDetail()
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function selectCategory(category) {
  selected.value = category
  await loadDetail()
}

async function onRangeChange() {
  await loadDetail()
}

async function requestRealtime() {
  if (!selected.value || detailLoading.value || realtimeLoading.value) return
  const sequence = ++detailSequence
  realtimeLoading.value = true
  try {
    const result = await fetchRealtimePredict(selected.value)
    if (sequence !== detailSequence) return
    predictData.value = result
    predictError.value = false
  } catch {
    // 主后端/网络异常时保留当前已加载图表；算法故障由后端正常200降级。
  } finally {
    if (sequence === detailSequence) realtimeLoading.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <div v-loading="loading" class="dashboard">
    <!-- 五品类卡片 -->
    <section class="cards">
      <AppCard
        v-for="c in cards"
        :key="c.category"
        :variant="c.category === selected ? 'soft' : 'light'"
        class="cat-card"
        :class="{ active: c.category === selected }"
        @click="selectCategory(c.category)"
      >
        <div class="cat-head">
          <span class="t-heading-md">{{ c.category }}</span>
          <AppPill variant="soft">{{ c.unit }}</AppPill>
        </div>
        <div class="price-row">
          <span class="t-display-md" :style="{ color: changeColor(c.changePct) }">
            {{ c.latestPrice ?? '—' }}
          </span>
          <span class="t-body-md" :style="{ color: changeColor(c.changePct) }">
            {{ changeText(c.changePct) }}
          </span>
        </div>
        <div class="t-micro">代表品名 {{ c.prodName }} · 数据日期 {{ c.latestDate || '—' }}</div>
      </AppCard>
    </section>

    <!-- 趋势 -->
    <AppCard variant="light" class="block">
      <div class="block-head">
        <div>
          <h3 class="t-heading-lg">均价趋势 — {{ selected || '—' }}</h3>
          <p class="t-caption">数据来源：北京新发地（已入库快照, 非实时爬取）</p>
        </div>
        <el-radio-group v-model="rangeDays" size="small" @change="onRangeChange">
          <el-radio-button v-for="o in rangeOptions" :key="o.value" :value="o.value">
            {{ o.label }}
          </el-radio-button>
        </el-radio-group>
      </div>
      <TrendChart v-if="trendSeries.length" :series-list="trendSeries" height="340px" />
      <el-empty v-else description="暂无数据" />
    </AppCard>

    <!-- 预测 -->
    <AppCard variant="light" class="block" v-loading="detailLoading">
      <div class="block-head">
        <AppPill :variant="predictData?.source === 'REALTIME' ? 'green' : 'soft'">
          {{ predictData?.source === 'REALTIME' ? '实时' : predictData?.degraded ? '预计算 · 已降级' : '预计算' }}
        </AppPill>
        <AppButton type="button" :disabled="detailLoading || realtimeLoading || !selected" @click="requestRealtime">
          {{ realtimeLoading ? '正在请求实时预测…' : '实时预测' }}
        </AppButton>
      </div>
      <el-alert v-if="predictData?.degraded" :title="predictData.message" type="warning" :closable="false" show-icon />
      <el-empty v-if="predictError" description="预测数据加载失败，请稍后重试（仅供参考）" />
      <PredictChart
        v-else-if="!detailLoading"
        :history="predictHistory"
        :predict="predictPoints"
        :model="predictData?.model || ''"
        :mape="predictData?.mapeTest ?? null"
        :disclaimer="predictData?.disclaimer || '预测结果仅供参考，不构成任何买卖建议'"
        :empty-message="predictData?.degraded ? '暂无可用预计算结果（仅供参考）' : '波动过大，暂不提供预测（仅供参考）'"
        height="380px"
      />
      <p class="t-micro disclaimer">
        ★ 预测结果仅供参考，不构成任何买卖建议（本系统为行政性监测与预警工具）
      </p>
    </AppCard>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--apr-space-lg);
}

.cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--apr-space-md);
}

.cat-card {
  cursor: pointer;
  padding: var(--apr-space-lg);
  transition: border-color 0.15s;
}

.cat-card.active {
  border: 1px solid var(--apr-primary);
}

.cat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--apr-space-sm);
}

.price-row {
  display: flex;
  align-items: baseline;
  gap: var(--apr-space-sm);
}

.block-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--apr-space-md);
}

.block-head h3 {
  margin: 0;
}

.block-head p {
  margin: var(--apr-space-xxs) 0 0;
}

.disclaimer {
  margin: var(--apr-space-sm) 0 0;
}

@media (max-width: 1023px) {
  .cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 767px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>
