<template>
  <RouterLink :to="`/mentions/${mention.id}`" class="row" :class="`row--${mention.sentiment.final_label}`">
    <div class="row__time">
      <span class="row__clock mono">{{ timeHM(mention.published_at) }}</span>
      <span class="row__day mono">{{ shortDay }}</span>
    </div>
    <div class="row__main">
      <div class="row__meta">
        <SourceTag :code="mention.source_code" :label="mention.source_label" />
        <span class="row__dot">·</span>
        <span class="row__group">{{ mention.group_name }}</span>
        <span class="row__dot">·</span>
        <span class="row__brand mono">{{ mention.brand_label }}</span>
        <span v-if="mention.sentiment.review_status === 'pending'" class="row__flag mono">待复核</span>
        <span v-else-if="mention.sentiment.review_status === 'corrected'" class="row__flag row__flag--fix mono">已修正</span>
      </div>
      <div class="row__title">{{ mention.title }}</div>
      <div class="row__excerpt">{{ mention.excerpt }}</div>
    </div>
    <div class="row__side">
      <SentimentChip :label="mention.sentiment.final_label" :score="mention.sentiment.score" small />
      <span class="row__hits mono">{{ mention.sentiment.negative_count }}↓ / {{ mention.sentiment.positive_count }}↑</span>
      <span class="row__engage mono">阅 {{ compactNumber(mention.engagement) }}</span>
    </div>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MentionItem } from '../../types/domain'
import { timeHM, compactNumber } from '../../utils/format'
import SentimentChip from '../common/SentimentChip.vue'
import SourceTag from '../common/SourceTag.vue'

const props = defineProps<{ mention: MentionItem }>()
const shortDay = computed(() => {
  const date = new Date(props.mention.published_at)
  return `${date.getMonth() + 1}/${date.getDate()}`
})
</script>

<style scoped>
.row {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr) 128px;
  gap: 14px;
  padding: 10px 10px 10px 0;
  border-bottom: 1px solid var(--rule-soft);
  border-left: 2px solid transparent;
  color: var(--ink);
  transition: background-color 150ms var(--ease), border-color 150ms var(--ease);
}
.row:hover {
  background: color-mix(in oklch, var(--ground-3) 60%, var(--ground));
  text-decoration: none;
}
.row--neg {
  border-left-color: var(--neg);
}
.row--pos {
  border-left-color: color-mix(in oklch, var(--pos) 70%, var(--ground));
}
.row--neu {
  border-left-color: var(--rule);
}
.row__time {
  display: flex;
  flex-direction: column;
  padding-top: 1px;
}
.row__clock {
  font-size: 13px;
  color: var(--ink);
  letter-spacing: 0.03em;
}
.row__day {
  font-size: 9px;
  color: var(--ink-faint);
}
.row__meta {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 10px;
  color: var(--ink-faint);
}
.row__dot {
  color: var(--rule);
}
.row__group {
  color: var(--ink-soft);
}
.row__brand {
  font-size: 9.5px;
}
.row__flag {
  font-size: 9px;
  color: var(--amber);
  border: 1px solid var(--amber-dim);
  padding: 0 4px;
}
.row__flag--fix {
  color: var(--watch);
  border-color: color-mix(in oklch, var(--watch) 55%, var(--ground));
}
.row__title {
  font-size: 13.5px;
  line-height: 1.35;
  margin-top: 3px;
  letter-spacing: -0.005em;
}
.row__excerpt {
  font-size: 11px;
  color: var(--ink-faint);
  margin-top: 3px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.row__side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  padding-top: 2px;
}
.row__hits,
.row__engage {
  font-size: 9px;
  color: var(--ink-faint);
}
@media (max-width: 720px) {
  .row {
    grid-template-columns: 46px minmax(0, 1fr);
  }
  .row__side {
    grid-column: 2;
    flex-direction: row;
    align-items: center;
    gap: 10px;
  }
}
</style>
