<template>
  <figure class="band">
    <figcaption class="band__cap">
      <span class="eyebrow">当日情感色带 · 24h</span>
      <span class="band__legend mono">
        <i class="k k--neg" />负 <i class="k k--neu" />中 <i class="k k--pos" />正
      </span>
    </figcaption>
    <svg class="band__svg" viewBox="0 0 720 96" preserveAspectRatio="none" role="img" :aria-label="aria">
      <line v-for="tick in 4" :key="tick" :y1="tick * 20" :y2="tick * 20" x1="0" x2="720" class="grid" />
      <g v-for="(point, index) in points" :key="point.hour">
        <rect
          :x="index * 30 + 3"
          :y="barY(point)"
          :width="24"
          :height="barH(point)"
          class="bar"
          :class="{ 'is-spike': isSpike(point) }"
        >
          <title>{{ label(point) }}</title>
        </rect>
        <rect
          :x="index * 30 + 3"
          :y="96 - segH(point.neg) - segH(point.neu) - segH(point.pos)"
          :width="24"
          :height="segH(point.pos)"
          class="seg seg--pos"
        />
        <rect
          :x="index * 30 + 3"
          :y="96 - segH(point.neg) - segH(point.neu)"
          :width="24"
          :height="segH(point.neu)"
          class="seg seg--neu"
        />
        <rect :x="index * 30 + 3" :y="96 - segH(point.neg)" :width="24" :height="segH(point.neg)" class="seg seg--neg" />
        <text v-if="index % 4 === 0" :x="index * 30 + 4" y="93" class="tick mono">{{ index }}</text>
      </g>
    </svg>
    <div class="band__foot mono">
      <span>峰值 {{ peakHour }}:00 · {{ peakCount }} 条</span>
      <span>刻度 = 小时；柱内 负/中/正 堆叠</span>
    </div>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BandPoint } from '../../types/domain'

const props = defineProps<{ points: BandPoint[] }>()

const total = (point: BandPoint) => point.pos + point.neu + point.neg
const max = computed(() => Math.max(6, ...props.points.map(total)))
const peak = computed(() => {
  let best = props.points[0]
  for (const point of props.points) {
    if (total(point) > total(best)) best = point
  }
  return best
})
const peakHour = computed(() => (peak.value ? peak.value.hour.toString().padStart(2, '0') : '--'))
const peakCount = computed(() => (peak.value ? total(peak.value) : 0))

function segH(value: number): number {
  return (value / max.value) * 86
}
function barH(point: BandPoint): number {
  return (total(point) / max.value) * 86
}
function barY(point: BandPoint): number {
  return 96 - barH(point)
}
function isSpike(point: BandPoint): boolean {
  return point.neg >= 3 && point.neg / Math.max(1, total(point)) > 0.5
}
function label(point: BandPoint): string {
  return `${point.hour}:00 · 负${point.neg} 中${point.neu} 正${point.pos}`
}
const aria = computed(() => `24 小时情感分布，峰值 ${peakHour.value} 点 ${peakCount.value} 条`)
</script>

<style scoped>
.band {
  margin: 0;
  border: 1px solid var(--rule-soft);
  background: color-mix(in oklch, var(--ground-2) 55%, var(--ground));
}
.band__cap {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 7px 10px 5px;
}
.band__legend {
  font-size: 9px;
  color: var(--ink-faint);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.k {
  width: 7px;
  height: 7px;
  display: inline-block;
}
.k--neg {
  background: var(--neg);
}
.k--neu {
  background: var(--neu);
}
.k--pos {
  background: var(--pos);
}
.band__svg {
  display: block;
  width: 100%;
  height: 96px;
}
.grid {
  stroke: var(--rule-soft);
  stroke-width: 0.5;
  opacity: 0.5;
}
.bar {
  fill: transparent;
  stroke: transparent;
}
.bar.is-spike {
  fill: color-mix(in oklch, var(--neg) 12%, transparent);
}
.seg {
  opacity: 0.92;
}
.seg--neg {
  fill: var(--neg);
}
.seg--neu {
  fill: var(--neu);
  opacity: 0.55;
}
.seg--pos {
  fill: var(--pos);
  opacity: 0.72;
}
.tick {
  font-size: 7px;
  fill: var(--ink-faint);
}
.band__foot {
  display: flex;
  justify-content: space-between;
  padding: 4px 10px 6px;
  font-size: 9px;
  color: var(--ink-faint);
  border-top: 1px solid var(--rule-soft);
}
</style>
