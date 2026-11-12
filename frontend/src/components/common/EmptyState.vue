<template>
  <div class="empty">
    <div class="empty__mark mono">{{ mark }}</div>
    <div class="empty__body">
      <div class="empty__title">{{ title }}</div>
      <p class="empty__desc">{{ description }}</p>
      <div v-if="$slots.action" class="empty__action"><slot name="action" /></div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ title: string; description: string; mark?: string }>(), { mark: '∅' })
</script>

<style scoped>
.empty {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 26px 18px;
  border: 1px dashed var(--rule-soft);
  background: color-mix(in oklch, var(--ground-2) 50%, var(--ground));
}
.empty__mark {
  font-size: 18px;
  color: var(--amber-dim);
  line-height: 1;
  padding-top: 2px;
}
.empty__title {
  font-size: 13.5px;
  color: var(--ink);
}
.empty__desc {
  font-size: 11.5px;
  color: var(--ink-faint);
  margin-top: 4px;
  max-width: 56ch;
}
.empty__action {
  margin-top: 10px;
}
</style>
