<template>
  <div class="err" role="alert">
    <div class="err__bar mono">{{ code ?? 'ERROR' }}</div>
    <div class="err__body">
      <div class="err__title">{{ title }}</div>
      <p class="err__message">{{ message }}</p>
      <p v-if="detail" class="err__detail mono">{{ detail }}</p>
      <div class="err__actions">
        <button v-if="retry" class="btn" @click="$emit('retry')">重试</button>
        <slot name="action" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{ title?: string; message: string; detail?: string; code?: string; retry?: boolean }>(),
  { title: '读数失败', retry: true },
)
defineEmits<{ retry: [] }>()
</script>

<style scoped>
.err {
  display: flex;
  border: 1px solid var(--neg);
  background: color-mix(in oklch, var(--neg) 8%, var(--ground));
}
.err__bar {
  writing-mode: vertical-rl;
  text-orientation: mixed;
  font-size: 9px;
  letter-spacing: 0.24em;
  color: var(--neg);
  padding: 8px 5px;
  border-right: 1px solid color-mix(in oklch, var(--neg) 45%, var(--ground));
}
.err__body {
  padding: 12px 14px;
}
.err__title {
  font-size: 13px;
  color: var(--ink);
}
.err__message {
  font-size: 11.5px;
  color: var(--ink-soft);
  margin-top: 3px;
}
.err__detail {
  font-size: 10px;
  color: var(--ink-faint);
  margin-top: 4px;
  word-break: break-all;
}
.err__actions {
  display: flex;
  gap: 8px;
  margin-top: 9px;
}
</style>
