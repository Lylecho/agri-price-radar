<script setup>
// 预测图组件 —— 历史实线 + 未来7天虚线（铁律: 必须展示模型、MAPE 与免责声明）
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  /** 历史点 [[date, value], ...] */
  history: { type: Array, default: () => [] },
  /** 预测点 [[date, value], ...] */
  predict: { type: Array, default: () => [] },
  model: { type: String, default: '' },
  mape: { type: [Number, String], default: null },
  disclaimer: { type: String, default: '预测结果仅供参考, 不构成任何买卖建议' },
  height: { type: String, default: '380px' },
  emptyMessage: { type: String, default: '波动过大，暂不提供预测（仅供参考）' },
})

const el = ref(null)
let chart = null

function buildOption() {
  const histDates = props.history.map((d) => d[0])
  const predDates = props.predict.map((d) => d[0])
  const allDates = [...histDates, ...predDates]
  // 预测序列前置 N-1 个 null 让虚线从最后一个实测点起笔, 视觉衔接
  const predData = new Array(Math.max(0, histDates.length - 1)).fill(null)
  if (histDates.length) {
    predData.push(props.history[histDates.length - 1][1])
  }
  props.predict.forEach((d) => predData.push(d[1]))

  const sub = [
    props.model ? `模型 ${props.model}` : '',
    props.mape != null ? `测试集 MAPE ${Number(props.mape).toFixed(3)}%` : '',
    props.disclaimer,
  ]
    .filter(Boolean)
    .join(' ｜ ')

  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 4, right: 8, textStyle: { color: '#707070' } },
    grid: { left: 56, right: 24, top: 82, bottom: 56 },
    title: {
      text: '未来7天预测',
      subtext: sub,
      left: 0,
      top: 0,
      textStyle: { fontSize: 14, fontWeight: 500, color: '#171717' },
      subtextStyle: { fontSize: 12, color: '#9a9a9a' },
    },
    xAxis: {
      type: 'category',
      data: allDates,
      axisLabel: { rotate: 45, interval: Math.max(0, Math.floor(allDates.length / 10)), color: '#707070' },
      axisLine: { lineStyle: { color: '#dfdfdf' } },
    },
    yAxis: {
      type: 'value',
      name: '均价(元/斤)',
      scale: true,
      nameTextStyle: { color: '#9a9a9a' },
      splitLine: { lineStyle: { color: '#efefef' } },
    },
    series: [
      {
        name: '历史均价',
        type: 'line',
        showSymbol: false,
        lineStyle: { width: 1.6, color: '#3ecf8e' },
        itemStyle: { color: '#3ecf8e' },
        data: [...props.history.map((d) => d[1]), ...new Array(predDates.length).fill(null)],
      },
      {
        name: props.model ? `预测(${props.model})` : '预测',
        type: 'line',
        showSymbol: true,
        symbolSize: 6,
        lineStyle: { width: 2.4, type: 'dashed', color: '#d94e41' },
        itemStyle: { color: '#d94e41' },
        data: predData,
      },
    ],
  }
}

function render() {
  if (!props.predict.length || !el.value) {
    if (chart) chart.dispose()
    chart = null
    return
  }
  if (!chart) chart = echarts.init(el.value)
  chart.setOption(buildOption(), true)
}

const onResize = () => chart && chart.resize()

onMounted(() => {
  render()
  window.addEventListener('resize', onResize)
})

watch(() => [props.history, props.predict, props.model, props.mape], render, { deep: true, flush: 'post' })

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (chart) chart.dispose()
})
</script>

<template>
  <div v-if="predict.length" ref="el" class="chart" :style="{ height }"></div>
  <el-empty v-else :description="emptyMessage" />
</template>

<style scoped>
.chart {
  width: 100%;
}
</style>
