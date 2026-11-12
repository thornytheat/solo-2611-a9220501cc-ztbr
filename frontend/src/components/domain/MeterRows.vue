<template>
  <div class="meters">
    <div v-for="row in rows" :key="row.label" class="meter">
      <span class="meter__label">{{ row.label }}</span>
      <span class="meter__track">
        <span class="meter__fill" :class="`meter__fill--${row.tone ?? 'amber'}`" :style="{ width: `${clamp(row.value) * 100}%` }" />
      </span>
      <span class="meter__value mono">{{ row.display ?? pct(row.value) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { pct } from '../../utils/format'

withDefaults(defineProps<{ rows: { label: string; value: number; display?: string; tone?: 'amber' | 'neg' | 'pos' | 'ink' }[] }>(), {})

function clamp(value: number): number {
  return Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0))
}
</script>

<style scoped>
.meters {
  display: flex;
  flex-direction: column;
}
.meter {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 92px 54px;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid color-mix(in oklch, var(--rule-soft) 55%, transparent);
}
.meter:last-child {
  border-bottom: 0;
}
.meter__label {
  font-size: 11.5px;
  color: var(--ink-soft);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meter__track {
  height: 3px;
  background: var(--ground-4);
  display: block;
}
.meter__fill {
  height: 100%;
  display: block;
  background: var(--amber);
  transition: width 420ms var(--ease);
}
.meter__fill--neg {
  background: var(--neg);
}
.meter__fill--pos {
  background: var(--pos);
}
.meter__fill--ink {
  background: var(--ink-faint);
}
.meter__value {
  font-size: 9.5px;
  color: var(--ink-faint);
  text-align: right;
}
</style>
