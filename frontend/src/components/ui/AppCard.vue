<script setup>
// AppCard —— DESIGN.md 卡片规范: 32px 内边距 / 12px 圆角 / 1px 发丝线(亮) 或暗底(暗)
// variant: light(白卡) | dark(canvas-night 暗卡) | soft(微灰卡)
defineProps({
  variant: { type: String, default: 'light' },
  shadow: { type: Boolean, default: false }, // 是否加 Level1 微抬升
})
</script>

<template>
  <div class="apr-card" :class="[`apr-card--${variant}`, { 'is-shadow': shadow }]">
    <slot />
  </div>
</template>

<style scoped>
.apr-card {
  padding: var(--apr-space-xxl);
  border-radius: var(--apr-radius-lg);
  font-size: var(--apr-fs-body-md);
  line-height: var(--apr-lh-body-md);
}

.apr-card--light {
  background: var(--apr-canvas);
  color: var(--apr-ink);
  border: 1px solid var(--apr-hairline);
}

.apr-card--soft {
  background: var(--apr-canvas-soft);
  color: var(--apr-ink);
  border: 1px solid var(--apr-hairline-cool);
}

/* 暗卡: 代码密集型内容/深色特性说明 */
.apr-card--dark {
  background: var(--apr-canvas-night);
  color: var(--apr-on-dark);
}

.is-shadow {
  box-shadow: var(--apr-shadow-1);
}
</style>
