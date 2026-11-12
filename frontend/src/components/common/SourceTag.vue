<template>
  <span class="stag mono" :class="`stag--${channel}`">
    <span class="stag__code">{{ code }}</span>
    <span class="stag__label">{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ code: string; label: string }>()
const CHANNEL: Record<string, string> = {
  news_wire: 'news',
  microblog: 'micro',
  vertical_forum: 'forum',
  video_agg: 'video',
}
const channel = computed(() => CHANNEL[props.code] ?? 'other')
</script>

<style scoped>
.stag {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  font-size: 9.5px;
  letter-spacing: 0.05em;
  color: var(--ink-faint);
}
.stag__code {
  text-transform: uppercase;
  color: var(--rule-bright);
  border-bottom: 1px solid var(--rule-soft);
}
.stag--micro .stag__code {
  color: var(--amber-dim);
}
.stag--video .stag__code {
  color: var(--watch);
}
.stag--forum .stag__code {
  color: var(--neu);
}
</style>
