<template>
  <div class="led" :class="[`led--${tone}`]">
    <div class="led__label">{{ label }}</div>
    <div class="led__row">
      <span class="led__value">{{ display }}</span>
      <span v-if="unit" class="led__unit">{{ unit }}</span>
    </div>
    <div v-if="hint" class="led__hint">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    value: number | string
    unit?: string
    hint?: string
    digits?: number
    tone?: 'amber' | 'neg' | 'pos' | 'ink'
  }>(),
  { tone: 'amber', digits: 3, unit: '', hint: '' },
)

const display = computed(() => {
  if (typeof props.value === 'string') return props.value
  const text = props.value.toString()
  return text.length >= props.digits ? text : text.padStart(props.digits, '0')
})
</script>

<style scoped>
.led {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 8px 10px 9px;
  border-left: 1px solid var(--rule-soft);
}
.led:first-child {
  border-left: 0;
  padding-left: 0;
}
.led__label {
  font-size: 9.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-faint);
}
.led__row {
  display: flex;
  align-items: baseline;
  gap: 3px;
}
.led__value {
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
  font-size: 26px;
  line-height: 1.05;
  letter-spacing: 0.02em;
  color: var(--amber);
  text-shadow: 0 0 12px color-mix(in oklch, var(--amber) 28%, transparent);
}
.led--neg .led__value {
  color: var(--neg);
  text-shadow: 0 0 12px color-mix(in oklch, var(--neg) 30%, transparent);
}
.led--pos .led__value {
  color: var(--pos);
  text-shadow: none;
}
.led--ink .led__value {
  color: var(--ink);
  text-shadow: none;
}
.led__unit {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--ink-faint);
}
.led__hint {
  font-size: 9.5px;
  color: var(--ink-faint);
}
</style>
