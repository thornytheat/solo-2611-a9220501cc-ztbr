<template>
  <span class="seal" :class="[`seal--${tone}`]">{{ label }}</span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ label: string; tone?: 'open' | 'claimed' | 'handled' | 'dismissed' | 'ink' }>(), {
  tone: 'ink',
})
</script>

<style scoped>
.seal {
  display: inline-block;
  font-family: var(--mono);
  font-size: 9.5px;
  letter-spacing: 0.08em;
  padding: 1px 6px;
  border: 1px solid var(--rule-soft);
  color: var(--ink-soft);
  white-space: nowrap;
}
.seal--open {
  border-color: var(--amber-dim);
  color: var(--amber);
}
.seal--claimed {
  border-color: var(--watch);
  color: var(--watch);
}
.seal--handled {
  border-color: color-mix(in oklch, var(--pos) 55%, var(--ground));
  color: var(--pos);
}
.seal--dismissed {
  color: var(--ink-faint);
}
.seal--ink {
  border-color: var(--rule);
  color: var(--ink-soft);
}
</style>
