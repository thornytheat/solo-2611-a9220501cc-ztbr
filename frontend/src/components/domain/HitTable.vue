<template>
  <div class="hits">
    <div class="hits__cap">
      <span class="eyebrow">情感证据链 · 逐词</span>
      <span class="hits__sum mono">
        正 {{ positive }} · 负 {{ negative }} · 否定 {{ negated }} · 程度 {{ degree }} · 反问 {{ rhetoric }}
      </span>
    </div>
    <table v-if="hits.length" class="hits__table">
      <thead>
        <tr>
          <th>词</th>
          <th>位置</th>
          <th>极性</th>
          <th>权重</th>
          <th>程度</th>
          <th>否定</th>
          <th class="num">贡献</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(hit, index) in hits" :key="index">
          <td class="hits__word">{{ hit.word }}</td>
          <td class="mono">{{ hit.offset }}</td>
          <td :class="hit.negated ? 'negated' : hit.polarity > 0 ? 'pos' : 'neg'">
            {{ hit.negated ? '翻转' : hit.polarity > 0 ? '正' : '负' }}
          </td>
          <td class="mono">{{ hit.weight.toFixed(2) }}</td>
          <td class="mono">{{ hit.degree ? `${hit.degree}×${hit.degree_ratio}` : '—' }}</td>
          <td class="mono">{{ hit.negated ? hit.negator : '—' }}</td>
          <td class="num mono" :class="hit.contribution < 0 ? 'neg' : hit.contribution > 0 ? 'pos' : ''">
            {{ hit.contribution.toFixed(3) }}
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="hits__empty">该条没有任何词典命中：分数为 0，按中性处理（不是「没有算」）。</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Hit } from '../../types/domain'

const props = defineProps<{ hits: Hit[]; positive?: number; negative?: number; negated?: number; degree?: number; rhetoric?: number }>()

const positive = computed(() => props.positive ?? props.hits.filter((hit) => hit.polarity > 0 && !hit.negated).length)
const negative = computed(() => props.negative ?? props.hits.filter((hit) => hit.polarity < 0 && !hit.negated).length)
const negated = computed(() => props.negated ?? props.hits.filter((hit) => hit.negated).length)
const degree = computed(() => props.degree ?? props.hits.filter((hit) => hit.degree).length)
const rhetoric = computed(() => props.rhetoric ?? 0)
</script>

<style scoped>
.hits {
  border-top: 1px solid var(--rule);
}
.hits__cap {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 9px 0 6px;
  gap: 10px;
  flex-wrap: wrap;
}
.hits__sum {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.hits__table {
  font-size: 11.5px;
}
.hits__table th {
  text-align: left;
  font-weight: 400;
  font-size: 9px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-faint);
  padding: 4px 8px 4px 0;
  border-bottom: 1px solid var(--rule-soft);
}
.hits__table td {
  padding: 4px 8px 4px 0;
  border-bottom: 1px solid color-mix(in oklch, var(--rule-soft) 55%, transparent);
  color: var(--ink-soft);
}
.hits__word {
  color: var(--ink);
}
.num {
  text-align: right;
}
.pos {
  color: var(--pos);
}
.neg {
  color: var(--neg);
}
.negated {
  color: var(--amber);
}
.hits__empty {
  font-size: 11.5px;
  color: var(--ink-faint);
  padding: 10px 0;
}
</style>
