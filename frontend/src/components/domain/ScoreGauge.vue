<template>
  <figure class="gauge">
    <svg viewBox="0 0 220 132" role="img" :aria-label="`情感分 ${score.toFixed(3)}，${labelText}`">
      <path :d="arcPath(0, 1)" class="track" />
      <path :d="arcPath(0, negBound)" class="zone zone--neg" />
      <path :d="arcPath(negBound, posBound)" class="zone zone--neu" />
      <path :d="arcPath(posBound, 1)" class="zone zone--pos" />
      <line :x1="center" :y1="center" :x2="needle.x" :y2="needle.y" class="needle" />
      <circle :cx="center" :cy="center" r="3.4" class="hub" />
      <text :x="center" :y="center - 26" text-anchor="middle" class="score">{{ scoreText }}</text>
      <text :x="center" :y="center - 12" text-anchor="middle" class="caption">{{ labelText }}</text>
      <text x="14" y="126" class="edge mono">-1.00</text>
      <text x="206" y="126" class="edge mono" text-anchor="end">+1.00</text>
    </svg>
    <figcaption class="gauge__foot mono">
      阈值 ±{{ threshold.toFixed(2) }} · 置信 {{ (confidence * 100).toFixed(0) }}%
    </figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SENTIMENT_LABELS } from '../../constants/enums'
import type { SentimentLabel } from '../../types/domain'

const props = withDefaults(
  defineProps<{ score: number; label: SentimentLabel; confidence?: number; threshold?: number }>(),
  { confidence: 0, threshold: 0.2 },
)

const center = 110
const radius = 84
const startAngle = Math.PI // 180°（左）
const endAngle = 0 // 0°（右）

function polar(value: number): { x: number; y: number } {
  const ratio = (value + 1) / 2
  const angle = startAngle - (startAngle - endAngle) * ratio
  return { x: center + radius * Math.cos(angle), y: 118 - radius * Math.sin(angle) }
}

function arcPath(from: number, to: number): string {
  const a = polar(from)
  const b = polar(to)
  const large = Math.abs(to - from) > 1 ? 0 : 0
  return `M ${a.x.toFixed(2)} ${a.y.toFixed(2)} A ${radius} ${radius} 0 0 1 ${b.x.toFixed(2)} ${b.y.toFixed(2)}`
}

const negBound = computed(() => -props.threshold)
const posBound = computed(() => props.threshold)
const needle = computed(() => polar(Math.max(-1, Math.min(1, props.score))))
const scoreText = computed(() => `${props.score > 0 ? '+' : ''}${props.score.toFixed(3)}`)
const labelText = computed(() => SENTIMENT_LABELS[props.label])
</script>

<style scoped>
.gauge {
  margin: 0;
  border: 1px solid var(--rule-soft);
  background: color-mix(in oklch, var(--ground-2) 50%, var(--ground));
}
.gauge svg {
  display: block;
  width: 100%;
  height: auto;
}
.track {
  fill: none;
  stroke: var(--ground-4);
  stroke-width: 7;
}
.zone {
  fill: none;
  stroke-width: 7;
  opacity: 0.85;
}
.zone--neg {
  stroke: color-mix(in oklch, var(--neg) 60%, var(--ground));
}
.zone--neu {
  stroke: color-mix(in oklch, var(--neu) 45%, var(--ground));
}
.zone--pos {
  stroke: color-mix(in oklch, var(--pos) 60%, var(--ground));
}
.needle {
  stroke: var(--amber);
  stroke-width: 1.6;
  stroke-linecap: round;
}
.hub {
  fill: var(--amber);
}
.score {
  font-family: var(--mono);
  font-size: 19px;
  fill: var(--ink);
  letter-spacing: 0.02em;
}
.caption {
  font-size: 9.5px;
  fill: var(--ink-faint);
  letter-spacing: 0.16em;
}
.edge {
  font-size: 7.5px;
  fill: var(--ink-faint);
}
.gauge__foot {
  padding: 5px 9px 6px;
  border-top: 1px solid var(--rule-soft);
  font-size: 9px;
  color: var(--ink-faint);
}
</style>
