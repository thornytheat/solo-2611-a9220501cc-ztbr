<template>
  <div class="page">
    <PageHeader
      kicker="burst watch · z = (x − μ) / σ"
      title="爆发预警看板"
      :description="`关键词组 × 小时桶计数，与过去 ${thresholds.baseline_days ?? 7} 天同小时基线比较；z>${thresholds.z_threshold ?? 3} 且 x≥max(${thresholds.min_count ?? 5}, 2μ) 触发，相邻窗口合并为事件。`"
    >
      <template #actions>
        <button v-if="auth.can('bursts:detect')" class="btn btn--amber" :disabled="store.busy" data-test="detect" @click="detect">
          {{ store.busy ? '检测中…' : '运行爆发检测' }}
        </button>
      </template>
    </PageHeader>

    <ErrorNotice v-if="store.error" :message="store.error" :retry="false" @retry="() => {}" />
    <div v-if="store.flash" class="flash rise">{{ store.flash }}</div>

    <section class="strip">
      <LedCounter label="危急" :value="dashboard?.level_counts.critical ?? 0" tone="neg" :digits="2" />
      <LedCounter label="预警" :value="dashboard?.level_counts.alert ?? 0" tone="amber" :digits="2" />
      <LedCounter label="关注" :value="dashboard?.level_counts.watch ?? 0" tone="pos" :digits="2" />
      <LedCounter label="事件合计" :value="dashboard?.total ?? 0" tone="ink" :digits="3" />
      <div class="strip__eval">
        <span class="eyebrow">评估日</span>
        <span class="mono strip__day">{{ dashboard?.eval_day ?? '—' }}</span>
        <span class="mono strip__algo">burst {{ detection?.algorithm_version ?? '1.0.0' }}</span>
      </div>
    </section>

    <div class="filters">
      <span class="eyebrow">等级</span>
      <button class="chip" :class="{ 'is-on': !store.level }" @click="setLevel('')">全部</button>
      <button
        v-for="level in store.levels"
        :key="level.value"
        class="chip"
        :class="{ 'is-on': store.level === level.value }"
        :data-test="`level-${level.value}`"
        @click="setLevel(level.value)"
      >{{ level.label }} <span class="chip__n mono">{{ level.count }}</span></button>
      <span class="filters__sep" />
      <span class="eyebrow">处置</span>
      <button class="chip" :class="{ 'is-on': !store.status }" @click="setStatus('')">全部</button>
      <button
        v-for="status in store.statuses"
        :key="status.value"
        class="chip"
        :class="{ 'is-on': store.status === status.value }"
        @click="setStatus(status.value)"
      >{{ status.label }} <span class="chip__n mono">{{ status.count }}</span></button>
    </div>

    <div class="grid">
      <section class="list">
        <div class="list__head">
          <span class="eyebrow">事件 {{ store.items.length }} 个</span>
          <span class="mono list__meta">按 z 降序</span>
        </div>
        <div v-if="!store.items.length" class="list__empty">
          <EmptyState
            title="还没有爆发事件"
            description="先运行一次检测：算法会按组 × 小时桶重算计数与基线，命中阈值的窗口才会写成事件。"
          >
            <template #action>
              <button v-if="auth.can('bursts:detect')" class="btn" @click="detect">运行爆发检测</button>
            </template>
          </EmptyState>
        </div>
        <button
          v-for="event in store.items"
          :key="event.id"
          class="event"
          :class="{ 'is-on': event.id === store.selectedId, [`event--${event.level}`]: true }"
          :data-test="`event-${event.group_code}`"
          @click="store.loadDetail(event.id)"
        >
          <div class="event__top">
            <LevelTag :level="event.level" />
            <span class="mono event__window">{{ windowLabel(event) }}</span>
            <StatusSeal :label="event.status_label" :tone="event.status" />
          </div>
          <div class="event__name">{{ event.group_name }}</div>
          <div class="event__meta mono">
            量 {{ event.count }} · μ {{ event.baseline_mean.toFixed(2) }} · σ {{ event.baseline_std.toFixed(2) }} · z
            {{ event.z_score.toFixed(2) }}
          </div>
          <div class="event__bar">
            <span :style="{ width: `${Math.min(100, (event.z_score / 8) * 100)}%` }" :class="`event__fill event__fill--${event.level}`" />
          </div>
        </button>
      </section>

      <section v-if="detail" class="detail rise">
        <div class="detail__head">
          <div>
            <div class="eyebrow">{{ detail.brand_label }} · {{ detail.group_code }}</div>
            <h2 class="detail__title">{{ detail.group_name }}</h2>
          </div>
          <div class="detail__tags">
            <LevelTag :level="detail.level" />
            <StatusSeal :label="detail.status_label" :tone="detail.status" />
          </div>
        </div>

        <dl class="metrics">
          <div><dt>窗口</dt><dd class="mono">{{ windowLabel(detail) }}</dd></div>
          <div><dt>量 x</dt><dd class="mono">{{ detail.count }}</dd></div>
          <div><dt>基线 μ</dt><dd class="mono">{{ detail.baseline_mean.toFixed(3) }}</dd></div>
          <div><dt>标准差 σ</dt><dd class="mono">{{ detail.baseline_std.toFixed(3) }}</dd></div>
          <div><dt>z</dt><dd class="mono detail__z">{{ detail.z_score.toFixed(2) }}</dd></div>
          <div><dt>阈值</dt><dd class="mono">z&gt;{{ detail.thresholds.z }} / x≥{{ detail.thresholds.min_count }}</dd></div>
        </dl>

        <BurstTrend
          :points="detail.trend"
          :window-start-hour="startHour"
          :window-end-hour="endHour"
        />

        <div class="baseline">
          <div class="baseline__cap">
            <span class="eyebrow">基线序列（过去 7 天同小时）</span>
            <span class="mono baseline__meta">σ&lt;{{ thresholds.sigma_floor ?? 1 }} 时按 {{ thresholds.sigma_floor ?? 1 }} 平滑</span>
          </div>
          <div class="baseline__bars">
            <div v-for="(value, index) in detail.baseline_series" :key="index" class="baseline__cell">
              <span class="baseline__bar" :style="{ height: `${barHeight(value)}px` }" :title="`day -${7 - index}: ${value}`" />
              <span class="mono baseline__v">{{ value }}</span>
            </div>
            <div class="baseline__cell baseline__cell--now">
              <span class="baseline__bar baseline__bar--now" :style="{ height: `${barHeight(detail.count)}px` }" />
              <span class="mono baseline__v">{{ detail.count }}</span>
            </div>
          </div>
        </div>

        <div class="actions">
          <div class="actions__row">
            <button
              v-if="auth.can('bursts:claim')"
              class="btn"
              :disabled="store.busy || detail.status === 'handled' || detail.status === 'dismissed'"
              data-test="claim"
              @click="claim"
            >认领</button>
            <button
              v-if="auth.can('bursts:dispose')"
              class="btn btn--amber"
              :disabled="store.busy || detail.status === 'handled' || detail.status === 'dismissed'"
              data-test="handle"
              @click="dispose('handled')"
            >标记已处置</button>
            <button
              v-if="auth.can('bursts:dispose')"
              class="btn btn--quiet"
              :disabled="store.busy || detail.status === 'handled' || detail.status === 'dismissed'"
              data-test="dismiss"
              @click="dispose('dismissed')"
            >排除（误报）</button>
            <span v-if="detail.claimed_by_email" class="mono actions__who">
              认领 {{ detail.claimed_by_email }} · {{ detail.claimed_at ? dateTime(detail.claimed_at) : '' }}
            </span>
          </div>
          <textarea
            v-model="disposeNote"
            class="field actions__note"
            rows="2"
            placeholder="处置说明，例如：已联系澄野咖啡客服核实批次 B24，启动召回公告"
            data-test="dispose-note"
          />
          <p v-if="detail.disposition_note" class="actions__done mono">
            处置备注：{{ detail.disposition_note }}
          </p>
        </div>

        <div class="window">
          <div class="window__cap">
            <span class="eyebrow">窗口内提及（按情感分升序）</span>
            <span class="mono window__meta">{{ detail.window_mentions.length }} 条样本</span>
          </div>
          <ul class="window__list">
            <li v-for="item in detail.window_mentions" :key="item.id" class="window__item">
              <RouterLink :to="`/mentions/${item.id}`" class="window__link">
                <SentimentChip :label="item.label" :score="item.score" small />
                <span class="window__title">{{ item.title }}</span>
                <span class="mono window__time">{{ timeHM(item.published_at) }}</span>
              </RouterLink>
            </li>
          </ul>
        </div>

        <div v-if="detail.sample_titles.length" class="samples">
          <span class="eyebrow">采集样本标题</span>
          <ul class="samples__list">
            <li v-for="title in detail.sample_titles" :key="title" class="samples__item">{{ title }}</li>
          </ul>
        </div>
      </section>
      <section v-else class="detail detail--empty">
        <EmptyState title="选择左侧事件" description="选中一个事件后，这里会显示逐小时趋势、基线序列、窗口内提及与处置动作。" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import EmptyState from '../components/common/EmptyState.vue'
import LedCounter from '../components/common/LedCounter.vue'
import LevelTag from '../components/common/LevelTag.vue'
import StatusSeal from '../components/common/StatusSeal.vue'
import SentimentChip from '../components/common/SentimentChip.vue'
import BurstTrend from '../components/domain/BurstTrend.vue'
import { useBurstStore } from '../stores/burstStore'
import { useMetaStore } from '../stores/metaStore'
import { useAuthStore } from '../stores/authStore'
import { dateTime, timeHM } from '../utils/format'
import type { BurstItem } from '../types/domain'

const store = useBurstStore()
const meta = useMetaStore()
const auth = useAuthStore()
const disposeNote = ref('')

const detail = computed(() => store.detail)
const dashboard = computed(() => store.dashboard)
const detection = computed(() => store.detection)
const thresholds = computed(() => store.list?.thresholds ?? { z_threshold: 3, min_count: 5, baseline_days: 7, sigma_floor: 1 })
const startHour = computed(() => (detail.value ? new Date(detail.value.window_start).getHours() : -1))
const endHour = computed(() => (detail.value ? new Date(detail.value.window_end).getHours() : -1))

function windowLabel(event: BurstItem): string {
  const start = new Date(event.window_start)
  const end = new Date(event.window_end)
  const fmt = (date: Date) => `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:00`
  return `${fmt(start)} – ${String(end.getHours()).padStart(2, '0')}:00`
}
function barHeight(value: number): number {
  const max = Math.max(1, ...(detail.value?.baseline_series ?? [1]), detail.value?.count ?? 1)
  return Math.max(2, (value / max) * 42)
}
function setLevel(value: string) {
  store.level = value
  void store.load()
}
function setStatus(value: string) {
  store.status = value
  void store.load()
}
async function detect() {
  disposeNote.value = ''
  await store.detect()
}
async function claim() {
  if (!detail.value) return
  await store.claim(detail.value.id)
}
async function dispose(status: string) {
  if (!detail.value) return
  await store.dispose(detail.value.id, status, disposeNote.value)
}

onMounted(async () => {
  await meta.load()
  await store.load()
})
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 13px;
}
.flash {
  font-size: 11.5px;
  color: var(--amber);
  border-left: 2px solid var(--amber);
  padding-left: 9px;
}
.strip {
  display: grid;
  grid-template-columns: repeat(4, auto) minmax(0, 1fr);
  align-items: center;
  gap: 4px 14px;
  border-top: 1px solid var(--rule);
  border-bottom: 1px solid var(--rule);
  padding: 10px 0;
}
.strip__eval {
  display: flex;
  align-items: baseline;
  gap: 8px;
  justify-content: flex-end;
}
.strip__day {
  font-size: 12px;
  color: var(--ink-soft);
}
.strip__algo {
  font-size: 9px;
  color: var(--ink-faint);
}
.filters {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
}
.filters__sep {
  width: 1px;
  height: 14px;
  background: var(--rule-soft);
  margin: 0 4px;
}
.chip__n {
  font-size: 8.5px;
  opacity: 0.7;
}
.grid {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}
.list {
  display: flex;
  flex-direction: column;
}
.list__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 5px;
  border-bottom: 1px solid var(--rule);
}
.list__meta {
  font-size: 9px;
  color: var(--ink-faint);
}
.list__empty {
  padding-top: 10px;
}
.event {
  display: flex;
  flex-direction: column;
  gap: 3px;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--rule-soft);
  border-left: 2px solid transparent;
  padding: 8px 8px 9px 9px;
  cursor: pointer;
  color: var(--ink);
  transition: background-color 150ms var(--ease), border-color 150ms var(--ease);
}
.event:hover {
  background: color-mix(in oklch, var(--ground-3) 55%, var(--ground));
}
.event.is-on {
  background: color-mix(in oklch, var(--ground-3) 82%, var(--ground));
}
.event--critical {
  border-left-color: var(--critical);
}
.event--alert {
  border-left-color: var(--alert);
}
.event--watch {
  border-left-color: var(--watch);
}
.event__top {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
}
.event__window {
  font-size: 9px;
  color: var(--ink-faint);
}
.event__name {
  font-size: 13px;
}
.event__meta {
  font-size: 9px;
  color: var(--ink-faint);
}
.event__bar {
  height: 2px;
  background: var(--ground-4);
  margin-top: 3px;
}
.event__fill {
  display: block;
  height: 100%;
  background: var(--watch);
}
.event__fill--critical {
  background: var(--critical);
}
.event__fill--alert {
  background: var(--alert);
}
.detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
  border-left: 1px solid var(--rule-soft);
  padding-left: 20px;
  min-width: 0;
}
.detail--empty {
  padding-top: 20px;
}
.detail__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--rule);
}
.detail__title {
  font-size: 22px;
  font-weight: 500;
  letter-spacing: -0.01em;
  margin-top: 2px;
}
.detail__tags {
  display: flex;
  gap: 6px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0;
  margin: 0;
  border-top: 1px solid var(--rule-soft);
  border-bottom: 1px solid var(--rule-soft);
}
.metrics div {
  padding: 6px 8px 7px;
  border-right: 1px solid var(--rule-soft);
}
.metrics div:last-child {
  border-right: 0;
}
.metrics dt {
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-faint);
}
.metrics dd {
  margin: 1px 0 0;
  font-size: 13px;
  color: var(--ink);
}
.detail__z {
  color: var(--critical);
}
.baseline__cap {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 6px;
}
.baseline__meta {
  font-size: 9px;
  color: var(--ink-faint);
}
.baseline__bars {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  border-bottom: 1px solid var(--rule-soft);
  padding-bottom: 2px;
}
.baseline__cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  flex: 1;
}
.baseline__bar {
  width: 100%;
  max-width: 26px;
  background: color-mix(in oklch, var(--ink-faint) 55%, var(--ground));
  display: block;
}
.baseline__bar--now {
  background: var(--neg);
}
.baseline__v {
  font-size: 9px;
  color: var(--ink-faint);
}
.baseline__cell--now .baseline__v {
  color: var(--neg);
}
.actions {
  border-top: 1px solid var(--rule);
  padding-top: 9px;
}
.actions__row {
  display: flex;
  gap: 7px;
  align-items: center;
  flex-wrap: wrap;
}
.actions__who {
  font-size: 9px;
  color: var(--ink-faint);
  margin-left: auto;
}
.actions__note {
  margin-top: 8px;
  resize: vertical;
  font-size: 11px;
}
.actions__done {
  font-size: 10px;
  color: var(--ink-soft);
  margin-top: 6px;
  border-left: 2px solid var(--watch);
  padding-left: 8px;
}
.window {
  border-top: 1px solid var(--rule);
  padding-top: 8px;
}
.window__cap {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 5px;
}
.window__meta {
  font-size: 9px;
  color: var(--ink-faint);
}
.window__list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.window__item {
  border-bottom: 1px solid var(--rule-soft);
}
.window__link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  color: var(--ink);
}
.window__link:hover {
  color: var(--amber);
  text-decoration: none;
}
.window__title {
  font-size: 11.5px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.window__time {
  font-size: 9px;
  color: var(--ink-faint);
}
.samples__list {
  list-style: none;
  margin: 5px 0 0;
  padding: 0;
}
.samples__item {
  font-size: 11px;
  color: var(--ink-faint);
  padding: 3px 0;
  border-bottom: 1px dotted var(--rule-soft);
}
@media (max-width: 1200px) {
  .metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .metrics div:nth-child(3) {
    border-right: 0;
  }
}
@media (max-width: 900px) {
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .detail {
    border-left: 0;
    padding-left: 0;
    border-top: 1px solid var(--rule);
    padding-top: 14px;
  }
  .strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .strip__eval {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
}
</style>
