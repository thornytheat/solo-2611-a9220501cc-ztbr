<template>
  <span class="ltag" :class="`ltag--${level}`">
    <span class="ltag__mark mono">{{ mark }}</span>
    <span class="ltag__text">{{ text }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BurstLevel } from '../../types/domain'
import { BURST_LEVEL_LABELS } from '../../constants/enums'

const props = defineProps<{ level: BurstLevel; label?: string }>()
const MARKS: Record<BurstLevel, string> = { critical: '!!!', alert: '!!', watch: '!' }
const text = computed(() => props.label ?? BURST_LEVEL_LABELS[props.level])
const mark = computed(() => MARKS[props.level])
</script>

<style scoped>
.ltag {
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
  padding: 1px 7px;
  font-size: 10.5px;
  border: 1px solid var(--rule-soft);
  color: var(--ink-soft);
  white-space: nowrap;
}
.ltag__mark {
  font-size: 8.5px;
  letter-spacing: 0.08em;
}
.ltag--critical {
  border-color: var(--critical);
  color: var(--critical);
}
.ltag--alert {
  border-color: var(--alert);
  color: var(--alert);
}
.ltag--watch {
  border-color: var(--watch);
  color: var(--watch);
}
</style>
