<script setup>
// AppCodeBlock —— DESIGN.md 代码块: canvas-night 深底 / 系统等宽字体 / 16px 内边距 / 6px 圆角
defineProps({
  code: { type: String, default: '' },
})
</script>

<template>
  <pre class="apr-code"><code>{{ code }}</code></pre>
</template>

<style scoped>
.apr-code {
  margin: 0;
  background: var(--apr-canvas-night);
  color: var(--apr-on-dark);
  font-family: var(--apr-font-mono);
  font-size: var(--apr-fs-code);
  line-height: var(--apr-lh-code);
  padding: var(--apr-space-lg);
  border-radius: var(--apr-radius-sm);
  overflow-x: auto;
  white-space: pre;
}
</style>
