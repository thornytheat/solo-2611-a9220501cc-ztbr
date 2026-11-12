<template>
  <span class="schip" :class="[`schip--${label}`, small ? 'schip--sm' : '']">
    <span class="schip__dot" />
    <span class="schip__label">{{ text }}</span>
    <span class="schip__score mono">{{ scoreText }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SentimentLabel } from '../../types/domain'
import { SENTIMENT_LABELS } from '../../constants/enums'

const props = withDefaults(
  defineProps<{ label: SentimentLabel; score?: number; small?: boolean }>(),
  { score: undefined, small: false },
)

const text = computed(() => SENTIMENT_LABELS[props.label] ?? props.label)
const scoreText = computed(() => (props.score === undefined ? '' : `${props.score > 0 ? '+' : ''}${props.score.toFixed(3)}`))
</script>

<style scoped>
.schip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--rule-soft);
  padding: 1px 7px;
  font-size: 10.5px;
  color: var(--ink-soft);
  white-space: nowrap;
}
.schip__dot {
  width: 4px;
  height: 4px;
  background: var(--neu);
}
.schip--neg {
  border-color: color-mix(in oklch, var(--neg) 55%, var(--ground));
  color: var(--neg);
}
.schip--neg .schip__dot {
  background: var(--neg);
}
.schip--pos {
  border-color: color-mix(in oklch, var(--pos) 50%, var(--ground));
  color: var(--pos);
}
.schip--pos .schip__dot {
  background: var(--pos);
}
.schip--sm {
  font-size: 9.5px;
  padding: 0 5px;
}
.schip__score {
  font-size: 9.5px;
  color: inherit;
  opacity: 0.85;
}
</style>
