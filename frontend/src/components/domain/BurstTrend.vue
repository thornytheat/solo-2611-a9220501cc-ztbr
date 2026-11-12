<template>
  <figure class="trend">
    <figcaption class="trend__cap">
      <span class="eyebrow">逐小时量与 7 天同小时基线</span>
      <span class="trend__legend mono">
        <i class="bar-k" />当日量 <i class="line-k" />基线 μ
      </span>
    </figcaption>
    <svg viewBox="0 0 720 150" preserveAspectRatio="none" role="img" :aria-label="aria">
      <line v-for="tick in 4" :key="`g${tick}`" :y1="tick * 30" :y2="tick * 30" x1="0" x2="720" class="grid" />
      <g v-for="(point, index) in points" :key="point.hour">
        <rect
          :x="index * 30 + 4"
          :y="140 - height(point.count)"
          :width="22"
          :height="height(point.count)"
          class="bar"
          :class="{ 'is-window': inWindow(point.hour) }"
        >
          <title>{{ point.hour }}:00 · 量 {{ point.count }} · 基线 {{ point.baseline }}</title>
        </rect>
        <circle v-if="point.baseline > 0" :cx="index * 30 + 15" :cy="140 - height(point.baseline)" r="1.8" class="dot" />
        <text v-if="index % 3 === 0" :x="index * 30 + 5" y="148" class="tick mono">{{ point.hour }}</text>
      </g>
      <polyline :points="baselinePolyline" class="baseline" />
      <rect :x="windowX" y="0" :width="windowWidth" height="140" class="window" />
    </svg>
    <div class="trend__foot mono">
      <span>窗口 {{ windowLabel }}</span>
      <span>峰值 {{ peakCount }} 条 / 基线 μ {{ baselineAvg.toFixed(2) }}</span>
    </div>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TrendPoint } from '../../types/domain'

const props = withDefaults(
  defineProps<{ points: TrendPoint[]; windowStartHour?: number; windowEndHour?: number }>(),
  { windowStartHour: -1, windowEndHour: -1 },
)

const peakCount = computed(() => Math.max(1, ...props.points.map((point) => point.count)))
const max = computed(() => Math.max(peakCount.value, ...props.points.map((point) => point.baseline)) * 1.15)
const baselineAvg = computed(() => {
  const values = props.points.map((point) => point.baseline)
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0
})

function height(value: number): number {
  return (value / max.value) * 136
}
function inWindow(hour: number): boolean {
  return props.windowStartHour >= 0 && hour >= props.windowStartHour && hour < props.windowEndHour
}
const windowX = computed(() => (props.windowStartHour >= 0 ? props.windowStartHour * 30 : 0))
const windowWidth = computed(() =>
  props.windowStartHour >= 0 ? Math.max(1, (props.windowEndHour - props.windowStartHour) * 30) : 0,
)
const windowLabel = computed(() =>
  props.windowStartHour >= 0
    ? `${String(props.windowStartHour).padStart(2, '0')}:00 – ${String(props.windowEndHour).padStart(2, '0')}:00`
    : '—',
)
const baselinePolyline = computed(() =>
  props.points
    .map((point, index) => `${index * 30 + 15},${(140 - height(point.baseline)).toFixed(1)}`)
    .join(' '),
)
const aria = computed(() => `逐小时爆发趋势，峰值 ${peakCount.value} 条`)
</script>

<style scoped>
.trend {
  margin: 0;
  border: 1px solid var(--rule-soft);
  background: color-mix(in oklch, var(--ground-2) 45%, var(--ground));
}
.trend__cap {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 7px 10px 2px;
}
.trend__legend {
  font-size: 9px;
  color: var(--ink-faint);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.bar-k {
  width: 7px;
  height: 7px;
  background: var(--amber-deep);
  display: inline-block;
}
.line-k {
  width: 10px;
  height: 1px;
  background: var(--ink-faint);
  display: inline-block;
}
.trend__svg {
  display: block;
  width: 100%;
  height: 150px;
}
.grid {
  stroke: var(--rule-soft);
  stroke-width: 0.5;
  opacity: 0.45;
}
.bar {
  fill: color-mix(in oklch, var(--ink-faint) 55%, var(--ground));
  transition: fill 160ms var(--ease);
}
.bar.is-window {
  fill: var(--neg);
  opacity: 0.92;
}
.dot {
  fill: var(--ink-faint);
}
.baseline {
  fill: none;
  stroke: var(--ink-faint);
  stroke-width: 1;
  stroke-dasharray: 3 3;
  opacity: 0.8;
}
.window {
  fill: color-mix(in oklch, var(--neg) 7%, transparent);
  stroke: color-mix(in oklch, var(--neg) 40%, transparent);
  stroke-dasharray: 2 3;
  stroke-width: 0.7;
}
.tick {
  font-size: 7.5px;
  fill: var(--ink-faint);
}
.trend__foot {
  display: flex;
  justify-content: space-between;
  padding: 4px 10px 6px;
  border-top: 1px solid var(--rule-soft);
  font-size: 9px;
  color: var(--ink-faint);
}
</style>
