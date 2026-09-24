<script setup>
// 设计规范展示页(StyleGuide) —— 把 frontend/DESIGN.md 的令牌与组件可视化
// 图表数据: 里程碑0入库快照(近90天五品类日度均价, 由 scripts/export_snapshot.py 导出)
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import snap from '@/assets/data/price_snapshot_90d.json'
import AppButton from '@/components/ui/AppButton.vue'
import AppCard from '@/components/ui/AppCard.vue'
import AppPill from '@/components/ui/AppPill.vue'
import AppCodeBlock from '@/components/ui/AppCodeBlock.vue'

/* ---------- 色板数据(token名 → hex, 与 tokens.css 同步) ---------- */
const colorGroups = [
  { title: '品牌与主色', items: [
    ['primary', '#3ecf8e'], ['primary-deep', '#24b47e'], ['primary-soft', '#4ade80'], ['on-primary', '#171717']] },
  { title: '文本墨色', items: [
    ['ink', '#171717'], ['ink-secondary', '#212121'], ['ink-mute', '#707070'], ['ink-mute-2', '#9a9a9a'], ['ink-faint', '#b2b2b2']] },
  { title: '画布与暗色', items: [
    ['canvas', '#ffffff'], ['canvas-soft', '#fafafa'], ['canvas-night', '#1c1c1c'], ['canvas-night-soft', '#202020'], ['on-dark', '#ffffff']] },
  { title: '发丝线灰阶', items: [
    ['hairline', '#dfdfdf'], ['hairline-strong', '#c7c7c7'], ['hairline-cool', '#ededed'], ['hairline-cool-2', '#efefef'], ['hairline-cool-3', '#d4d4d4']] },
  { title: '点缀色(仅图表/标识)', items: [
    ['accent-purple', '#6b01c2'], ['accent-violet', '#644fc1'], ['accent-yellow', '#ffdb13'], ['accent-tomato', '#ff2201'], ['accent-pink', '#c7007e'], ['accent-indigo', '#054cff'], ['accent-crimson', '#e2005a']] },
]

/* ---------- 字阶 ---------- */
const typeScale = [
  ['t-display-xxl', 'display-xxl', '64 / 500 / 1.1 / -1.92px', '菜价雷达 Price Radar'],
  ['t-display-xl', 'display-xl', '48 / 500 / 1.1 / -1.44px', '走势 · 监测 · 预警'],
  ['t-display-lg', 'display-lg', '36 / 500 / 1.15 / -0.72px', '批发价格监测'],
  ['t-display-md', 'display-md', '28 / 500 / 1.2 / -0.42px', '品类价格趋势'],
  ['t-heading-lg', 'heading-lg', '22 / 500 / 1.2', '近90天均价走势'],
  ['t-heading-md', 'heading-md', '18 / 500 / 1.4', '环比涨跌幅'],
  ['t-body-lg', 'body-lg', '18 / 400 / 1.55', '本系统为行政性监测与预警工具，所有预测结果仅供参考。'],
  ['t-body-md', 'body-md', '16 / 400 / 1.5', '数据来源：北京新发地批发市场每日发布的最低价、最高价与均价。'],
  ['t-caption', 'caption', '13 / 400 / 1.45', '辅助说明与脚注文字使用 caption 层级。'],
  ['t-micro', 'micro', '12 / 400 / 1.45', '药丸标签与法律声明使用 micro 层级。'],
  ['t-code', 'code', '14 / 400 / 1.5 (mono)', 'SELECT prod_name, AVG(avg_price) FROM price_daily;'],
]

/* ---------- 间距 / 圆角 / 阴影 ---------- */
const spacings = [
  ['xxs', '2px'], ['xs', '4px'], ['sm', '8px'], ['md', '12px'],
  ['lg', '16px'], ['xl', '24px'], ['xxl', '32px'], ['huge', '64px'],
]
const radiuses = [
  ['xs', '4px', '输入框'], ['sm', '6px', '按钮/代码块'], ['md', '8px', '紧凑卡片'],
  ['lg', '12px', '特性卡/mockup'], ['xl', '16px', '模态框'], ['full', '9999px', '药丸'],
]
const shadows = [
  ['1', '0 1px 3px rgba(0,0,0,.06)', '卡片微抬升'],
  ['2', '0 8px 24px rgba(0,0,0,.08)', '悬浮面板'],
  ['3', '0 16px 48px rgba(0,0,0,.12)', '模态/深层'],
]

/* ---------- Do / Don't ---------- */
const dos = [
  '翡翠绿只用于实心 CTA 与品牌点缀，每视口一个实心绿元素',
  '展示层统一 weight 500 + 负字距（工程感的紧密度）',
  '按钮一律 6px 方角，永不胶囊形',
  '绿底按钮配墨色文字 #171717，不是白色',
  '代码块使用系统等宽字体',
  '卡片 = 1px 发丝线 + 12px 圆角，不加渐变',
]
const donts = [
  '点缀色（紫/黄/粉）不得用作系统色，仅限图表与标识',
  '展示层字重不超过 500',
  '禁止胶囊形按钮',
  '禁止绿底白字',
  '禁止大气渐变背景——白画布本身就是设计',
  '不在用户请求时现场爬取数据（快照策略）',
]

/* ---------- 图表(M4 推荐配色试用: 主系列翡翠绿 + 墨色/点缀灰阶) ---------- */
const SERIES_COLORS = ['#3ecf8e', '#171717', '#054cff', '#644fc1', '#707070']
const chartEl = ref(null)
let chart = null

const onResize = () => chart && chart.resize()

onMounted(() => {
  chart = echarts.init(chartEl.value)
  chart.setOption({
    color: SERIES_COLORS,
    tooltip: { trigger: 'axis', valueFormatter: (v) => (v == null ? '-' : `${v} 元/斤`) },
    legend: { top: 4, textStyle: { color: '#707070' } },
    grid: { left: 56, right: 24, top: 40, bottom: 56 },
    xAxis: {
      type: 'category',
      data: snap.dates,
      axisLabel: { rotate: 45, interval: 13, color: '#707070' },
      axisLine: { lineStyle: { color: '#dfdfdf' } },
    },
    yAxis: { type: 'value', name: '均价(元/斤)', scale: true, axisLine: { show: false } },
    series: snap.series.map((s) => ({
      name: s.name,
      type: 'line',
      showSymbol: false,
      lineStyle: { width: 1.6 },
      data: s.values,
    })),
  })
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (chart) chart.dispose()
})

const sqlSample = `-- 预计算表示例(蓝图 §7 算法方案)
SELECT prod_name, trade_date, avg_price
FROM price_daily
WHERE prod_name = '大白菜'
  AND trade_date >= DATE '2026-01-01'
ORDER BY trade_date;`
</script>

<template>
  <div class="page">
    <!-- ============ 顶部导航样例(nav-bar-light) ============ -->
    <header class="nav">
      <div class="apr-container nav-inner">
        <div class="brand">
          <span class="brand-dot"></span>
          <span class="t-heading-md">菜价雷达</span>
        </div>
        <nav class="nav-links t-body-md">
          <a href="#colors">色彩</a>
          <a href="#type">字阶</a>
          <a href="#layout">版式</a>
          <a href="#components">组件</a>
          <a href="#chart">图表</a>
        </nav>
        <AppButton variant="primary">进入系统(预留)</AppButton>
      </div>
    </header>

    <!-- ============ Hero ============ -->
    <section class="apr-container hero">
      <AppPill variant="green">设计系统 v0.1</AppPill>
      <h1 class="t-display-xxl hero-title">清晰即设计。</h1>
      <p class="t-body-lg hero-lead">
        菜价雷达界面设计语言：白画布上的近黑墨色阶梯，唯一的色彩事件是翡翠绿主色。
        本页为设计令牌与组件的可视化规范，所有数值源自 frontend/DESIGN.md。
      </p>
      <p class="t-caption">数据快照生成于 {{ snap.generated_at }} · {{ snap.source }} · 近{{ snap.days }}天 × {{ snap.series.length }}品类</p>
    </section>

    <!-- ============ 色板 ============ -->
    <section id="colors" class="apr-section">
      <div class="apr-container">
        <h2 class="t-display-md sec-title">色彩令牌</h2>
        <p class="t-body-md sec-desc">近黑非纯黑；绿色克制使用；点缀色仅限图表与标识。</p>
        <div v-for="g in colorGroups" :key="g.title" class="color-group">
          <h3 class="t-heading-md">{{ g.title }}</h3>
          <div class="swatch-grid">
            <div v-for="[name, hex] in g.items" :key="name" class="swatch">
              <div class="swatch-chip" :style="{ background: hex }" :class="{ 'is-white': hex === '#ffffff' }"></div>
              <div class="t-caption">--apr-{{ name }}</div>
              <div class="t-micro">{{ hex }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ 字阶 ============ -->
    <section id="type" class="apr-section">
      <div class="apr-container">
        <h2 class="t-display-md sec-title">字阶</h2>
        <p class="t-body-md sec-desc">Inter(拉丁) + Noto Sans SC(中文)，npm 本地打包，无外网 CDN 依赖。</p>
        <div class="type-table">
          <div v-for="[cls, name, spec, sample] in typeScale" :key="name" class="type-row">
            <div class="type-sample" :class="cls">{{ sample }}</div>
            <div class="type-meta">
              <div class="t-caption">{{ name }}</div>
              <div class="t-micro">{{ spec }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ 版式: 间距/圆角/阴影 ============ -->
    <section id="layout" class="apr-section">
      <div class="apr-container">
        <h2 class="t-display-md sec-title">间距 · 圆角 · 阴影</h2>
        <p class="t-body-md sec-desc">8px 基准间距；6px 方角按钮；四级海拔。</p>
        <div class="layout-grid">
          <div class="layout-block">
            <h3 class="t-heading-md">间距刻度</h3>
            <div v-for="[name, val] in spacings" :key="name" class="space-row">
              <span class="t-caption">{{ name }} / {{ val }}</span>
              <span class="space-bar" :style="{ width: val }"></span>
            </div>
          </div>
          <div class="layout-block">
            <h3 class="t-heading-md">圆角刻度</h3>
            <div class="radius-grid">
              <div v-for="[name, val, use] in radiuses" :key="name" class="radius-box" :style="{ borderRadius: val }">
                <div class="t-caption">{{ val }}</div>
                <div class="t-micro">{{ use }}</div>
              </div>
            </div>
          </div>
          <div class="layout-block">
            <h3 class="t-heading-md">海拔(阴影)</h3>
            <div class="radius-grid">
              <div v-for="[lvl, shadow, use] in shadows" :key="lvl" class="shadow-box" :style="{ boxShadow: shadow }">
                <div class="t-caption">Level {{ lvl }}</div>
                <div class="t-micro">{{ use }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ 组件 ============ -->
    <section id="components" class="apr-section">
      <div class="apr-container">
        <h2 class="t-display-md sec-title">组件</h2>
        <p class="t-body-md sec-desc">品牌组件(左) 与 Element Plus 定制后(右) 对照。</p>

        <h3 class="t-heading-md">按钮 · AppButton / ElButton</h3>
        <div class="demo-row">
          <AppButton variant="primary">主操作</AppButton>
          <AppButton variant="outline">次操作</AppButton>
          <AppButton variant="on-dark">暗面按钮</AppButton>
          <AppButton variant="link">文字按钮</AppButton>
          <el-button type="primary">EP 主按钮</el-button>
          <el-button>EP 次按钮</el-button>
        </div>

        <h3 class="t-heading-md">卡片 · AppCard</h3>
        <div class="card-grid">
          <AppCard variant="light" shadow>
            <h4 class="t-heading-lg">特性卡(亮)</h4>
            <p class="t-body-md">白底 + 1px 发丝线 + 12px 圆角 + 32px 内边距，可叠加 Level 1 微抬升。</p>
          </AppCard>
          <AppCard variant="dark">
            <h4 class="t-heading-lg">特性卡(暗)</h4>
            <p class="t-body-md">canvas-night 深底，用于代码密集内容；大屏(1920×1080) 将沿用此暗色系(M3 决策)。</p>
          </AppCard>
          <AppCard variant="soft">
            <h4 class="t-heading-lg">微灰卡</h4>
            <p class="t-body-md">canvas-soft 交替分区底色，承载次要信息。</p>
          </AppCard>
        </div>

        <h3 class="t-heading-md">标签 · AppPill</h3>
        <div class="demo-row">
          <AppPill variant="green">NEW 预测上线</AppPill>
          <AppPill variant="soft">白菜类</AppPill>
          <AppPill variant="soft">蛋类</AppPill>
        </div>

        <h3 class="t-heading-md">代码块 · AppCodeBlock 与输入框</h3>
        <div class="card-grid">
          <AppCodeBlock :code="sqlSample" />
          <div class="input-demo">
            <el-input placeholder="搜索品类, 如: 大白菜" />
            <el-date-picker type="date" placeholder="选择日期" style="width: 100%" />
          </div>
        </div>
      </div>
    </section>

    <!-- ============ 图表配色试用 ============ -->
    <section id="chart" class="apr-section">
      <div class="apr-container">
        <h2 class="t-display-md sec-title">图表配色(试用)</h2>
        <p class="t-body-md sec-desc">
          M4 推荐方案：主系列翡翠绿，辅以墨色与点缀色阶；环比/涨跌类图表沿用「红涨绿跌」惯例。
          数据为里程碑0入库的真实快照，仅作配色演示。
        </p>
        <div ref="chartEl" class="chart"></div>
      </div>
    </section>

    <!-- ============ Do / Don't ============ -->
    <section class="apr-section">
      <div class="apr-container">
        <h2 class="t-display-md sec-title">Do &amp; Don't</h2>
        <div class="card-grid two">
          <AppCard variant="light">
            <h4 class="t-heading-lg">✓ Do</h4>
            <ul class="rule-list t-body-md">
              <li v-for="r in dos" :key="r">{{ r }}</li>
            </ul>
          </AppCard>
          <AppCard variant="dark">
            <h4 class="t-heading-lg">✗ Don't</h4>
            <ul class="rule-list t-body-md">
              <li v-for="r in donts" :key="r">{{ r }}</li>
            </ul>
          </AppCard>
        </div>
      </div>
    </section>

    <!-- ============ Footer(footer-light) ============ -->
    <footer class="footer">
      <div class="apr-container t-caption">
        菜价雷达 · 农产品价格监测与短期预测系统（毕业设计） · 预测结果仅供参考，不构成任何买卖建议
      </div>
    </footer>
  </div>
</template>

<style scoped>
.page { background: var(--apr-canvas); }

/* 导航 */
.nav { position: sticky; top: 0; z-index: 10; background: var(--apr-canvas); border-bottom: 1px solid var(--apr-hairline-cool); }
.nav-inner { display: flex; align-items: center; gap: var(--apr-space-lg); padding-top: var(--apr-space-lg); padding-bottom: var(--apr-space-lg); }
.brand { display: flex; align-items: center; gap: var(--apr-space-sm); margin-right: auto; }
.brand-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--apr-primary); }
.nav-links { display: flex; gap: var(--apr-space-lg); }
.nav-links a:hover { color: var(--apr-primary-deep); text-decoration: underline; }

/* Hero */
.hero { padding: var(--apr-space-huge) var(--apr-space-xl) var(--apr-space-xxl); display: flex; flex-direction: column; gap: var(--apr-space-md); align-items: flex-start; }
.hero-title { margin: 0; }
.hero-lead { max-width: 640px; color: var(--apr-ink-secondary); }

/* 分区标题 */
.sec-title { margin: 0 0 var(--apr-space-sm); }
.sec-desc { margin: 0 0 var(--apr-space-xl); color: var(--apr-ink-mute); max-width: 720px; }

/* 色板 */
.color-group { margin-bottom: var(--apr-space-xl); }
.swatch-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--apr-space-md); }
.swatch { border: 1px solid var(--apr-hairline-cool); border-radius: var(--apr-radius-md); padding: var(--apr-space-sm); }
.swatch-chip { height: 56px; border-radius: var(--apr-radius-xs); margin-bottom: var(--apr-space-xs); }
.swatch-chip.is-white { border: 1px solid var(--apr-hairline); }

/* 字阶 */
.type-table { display: flex; flex-direction: column; }
.type-row { display: grid; grid-template-columns: 1fr 220px; gap: var(--apr-space-lg); align-items: center; padding: var(--apr-space-md) 0; border-bottom: 1px solid var(--apr-hairline-cool); }
.type-sample { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 版式 */
.layout-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--apr-space-lg); }
.space-row { display: flex; align-items: center; gap: var(--apr-space-md); margin-bottom: var(--apr-space-sm); }
.space-bar { height: 12px; background: var(--apr-primary); border-radius: 2px; }
.radius-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--apr-space-md); }
.radius-box { height: 72px; border: 1px solid var(--apr-hairline-strong); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; background: var(--apr-canvas-soft); }
.shadow-box { height: 72px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; background: var(--apr-canvas); border-radius: var(--apr-radius-md); }

/* 组件演示 */
.demo-row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--apr-space-md); margin-bottom: var(--apr-space-xl); }
.card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--apr-space-lg); margin-bottom: var(--apr-space-xl); }
.card-grid.two { grid-template-columns: repeat(2, 1fr); }
.input-demo { display: flex; flex-direction: column; gap: var(--apr-space-md); justify-content: center; padding: var(--apr-space-lg); border: 1px dashed var(--apr-hairline-strong); border-radius: var(--apr-radius-lg); }
.rule-list { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: var(--apr-space-xs); }

/* 图表 */
.chart { width: 100%; height: 420px; border: 1px solid var(--apr-hairline-cool); border-radius: var(--apr-radius-lg); padding: var(--apr-space-md); }

/* Footer */
.footer { border-top: 1px solid var(--apr-hairline-cool); padding: var(--apr-space-huge) 0; background: var(--apr-canvas); }

/* 响应式: 1024 收两列, 768 收单列 */
@media (max-width: 1023px) {
  .swatch-grid { grid-template-columns: repeat(3, 1fr); }
  .layout-grid, .card-grid, .card-grid.two { grid-template-columns: repeat(2, 1fr); }
  .nav-links { display: none; }
}
@media (max-width: 767px) {
  .swatch-grid, .layout-grid, .card-grid, .card-grid.two, .radius-grid { grid-template-columns: 1fr; }
  .type-row { grid-template-columns: 1fr; }
}
</style>
