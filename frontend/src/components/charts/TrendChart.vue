<script setup>
// 趋势折线图组件 —— 多系列日度均价（封装 ECharts, 复用 M4 图表配色）
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  /** [{ name: '大白菜', data: [[dateStr, value| null], ...] }] */
  seriesList: { type: Array, default: () => [] },
  yName: { type: String, default: '均价(元/斤)' },
  height: { type: String, default: '360px' },
})

// 图表配色: 主系列翡翠绿 + 墨色/点缀色阶（蓝图 M4 决策）
const PALETTE = ['#3ecf8e', '#171717', '#054cff', '#644fc1', '#707070']

const el = ref(null)
let chart = null

function buildOption() {
  const dates = props.seriesList.length ? props.seriesList[0].data.map((d) => d[0]) : []
  return {
    color: PALETTE,
    tooltip: { trigger: 'axis' },
    legend: { top: 4, textStyle: { color: '#707070' } },
    grid: { left: 56, right: 24, top: 44, bottom: 56 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 45, interval: Math.max(0, Math.floor(dates.length / 10)), color: '#707070' },
      axisLine: { lineStyle: { color: '#dfdfdf' } },
    },
    yAxis: {
      type: 'value',
      name: props.yName,
      scale: true,
      nameTextStyle: { color: '#9a9a9a' },
      splitLine: { lineStyle: { color: '#efefef' } },
    },
    series: props.seriesList.map((s) => ({
      name: s.name,
      type: 'line',
      showSymbol: false,
      smooth: false,
      lineStyle: { width: 1.8 },
      data: s.data.map((d) => d[1]),
    })),
  }
}

function render() {
  if (!chart) return
  chart.setOption(buildOption(), true)
}

const onResize = () => chart && chart.resize()

onMounted(() => {
  chart = echarts.init(el.value)
  render()
  window.addEventListener('resize', onResize)
})

watch(() => props.seriesList, render, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (chart) chart.dispose()
})
</script>

<template>
  <div ref="el" class="chart" :style="{ height }"></div>
</template>

<style scoped>
.chart {
  width: 100%;
}
</style>
