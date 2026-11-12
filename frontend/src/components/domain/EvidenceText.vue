<template>
  <div class="ev">
    <p class="ev__body">
      <template v-for="(segment, index) in segments" :key="index">
        <mark v-if="segment.hit" :class="['hl', `hl--${role(segment.hit)}`]" :title="title(segment.hit)">
          {{ segment.text }}
        </mark>
        <span v-else>{{ segment.text }}</span>
      </template>
    </p>
    <div class="ev__legend mono">
      <span><i class="lg lg--neg" />负向词</span>
      <span><i class="lg lg--pos" />正向词</span>
      <span><i class="lg lg--negated" />否定翻转</span>
      <span class="ev__offset">offset 对应归一化正文，后端给出</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Hit } from '../../types/domain'
import { splitByHits, hitRole } from '../../utils/highlight'

const props = defineProps<{ body: string; hits: Hit[] }>()
const segments = computed(() => splitByHits(props.body, props.hits))
const role = (hit: Hit) => hitRole(hit)
function title(hit: Hit): string {
  const parts = [`${hit.word}`, `权重 ${hit.weight}`, `极向 ${hit.polarity > 0 ? '+' : '-'}`]
  if (hit.negated) parts.push(`否定 ${hit.negator}`)
  if (hit.degree) parts.push(`程度 ${hit.degree}×${hit.degree_ratio}`)
  parts.push(`贡献 ${hit.contribution}`)
  return parts.join(' · ')
}
</script>

<style scoped>
.ev__body {
  font-size: 14px;
  line-height: 1.95;
  color: var(--ink-soft);
  letter-spacing: 0.005em;
  white-space: pre-wrap;
}
.hl {
  background: transparent;
  color: var(--neg);
  border-bottom: 1px solid var(--neg);
  padding: 0 1px;
}
.hl--pos {
  color: var(--pos);
  border-bottom-color: var(--pos);
}
.hl--negated {
  color: var(--amber);
  border-bottom-color: var(--amber);
  text-decoration: line-through;
  text-decoration-thickness: 1px;
}
.ev__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
  padding-top: 7px;
  border-top: 1px solid var(--rule-soft);
  font-size: 9px;
  color: var(--ink-faint);
}
.lg {
  width: 8px;
  height: 1px;
  display: inline-block;
  vertical-align: middle;
  margin-right: 4px;
}
.lg--neg {
  background: var(--neg);
  height: 2px;
}
.lg--pos {
  background: var(--pos);
  height: 2px;
}
.lg--negated {
  background: var(--amber);
  height: 2px;
}
.ev__offset {
  margin-left: auto;
  opacity: 0.75;
}
</style>
