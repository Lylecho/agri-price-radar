<script setup>
// AppPill —— DESIGN.md 药丸标签: 全圆角 / micro 字阶 / 2px 8px 内边距
// variant: green(绿底墨字, "new/精选"指示) | soft(微灰底, 中性标签)
defineProps({
  variant: { type: String, default: 'soft' },
})
</script>

<template>
  <span class="apr-pill" :class="`apr-pill--${variant}`">
    <slot />
  </span>
</template>

<style scoped>
.apr-pill {
  display: inline-block;
  padding: var(--apr-space-xxs) var(--apr-space-sm);
  border-radius: var(--apr-radius-full);
  font-size: var(--apr-fs-micro);
  font-weight: 400;
  line-height: var(--apr-lh-micro);
  white-space: nowrap;
}

/* 绿色药丸: 翡翠绿要克制使用(每视口一个实心绿元素为宜) */
.apr-pill--green {
  background: var(--apr-primary);
  color: var(--apr-on-primary);
}

.apr-pill--soft {
  background: var(--apr-canvas-soft);
  color: var(--apr-ink);
  border: 1px solid var(--apr-hairline-cool);
}
</style>
