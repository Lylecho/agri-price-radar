<script setup>
// AppButton —— DESIGN.md 按钮规范: 6px 方角 / button-md 字阶 / 8px 16px 内边距
// variant: primary(绿底墨字) | outline(白底描边) | onDark(暗面) | link(纯文字)
defineProps({
  variant: { type: String, default: 'primary' },
})
</script>

<template>
  <button class="apr-btn" :class="`apr-btn--${variant}`">
    <slot />
  </button>
</template>

<style scoped>
.apr-btn {
  border: none;
  cursor: pointer;
  font-family: var(--apr-font-family);
  font-size: var(--apr-fs-button-md);
  font-weight: 500;
  line-height: var(--apr-lh-button-md);
  padding: var(--apr-space-sm) var(--apr-space-lg);
  border-radius: var(--apr-radius-sm);
  transition: background 0.15s ease;
}

/* 招牌主钮: 绿底 + 墨字, 悬停亮绿, 按压深绿 */
.apr-btn--primary {
  background: var(--apr-primary);
  color: var(--apr-on-primary);
}
.apr-btn--primary:hover {
  background: var(--apr-primary-soft);
}
.apr-btn--primary:active {
  background: var(--apr-primary-deep);
}

/* 次级: 白底 + 发丝线描边 */
.apr-btn--outline {
  background: var(--apr-canvas);
  color: var(--apr-ink);
  border: 1px solid var(--apr-hairline-strong);
}
.apr-btn--outline:hover {
  background: var(--apr-canvas-soft);
}

/* 暗面按钮: 用于深色表面 */
.apr-btn--on-dark {
  background: var(--apr-canvas-night);
  color: var(--apr-on-dark);
}
.apr-btn--on-dark:hover {
  background: var(--apr-canvas-night-soft);
}

/* 纯文字链接钮: 悬停下划线 */
.apr-btn--link {
  background: transparent;
  color: var(--apr-ink);
  padding: 0;
  border-radius: var(--apr-radius-xs);
}
.apr-btn--link:hover {
  text-decoration: underline;
}
</style>
