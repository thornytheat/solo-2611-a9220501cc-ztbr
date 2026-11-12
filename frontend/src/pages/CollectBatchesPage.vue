<template>
  <div class="page">
    <PageHeader
      kicker="backfill batches · 断点续跑 · 逐源对账"
      title="补采批次"
      description="选择品牌、来源与时间段生成可跟踪批次：逐源处理并记录待处理 / 已入库 / 重复 / 失败。中断后从断点续跑，重试只处理失败来源，重复运行不新增提及。"
    />

    <EmptyState
      v-if="!canRun"
      title="当前角色无权访问补采批次"
      description="补采批次仅对舆情总监与值班分析师开放；品牌方账号可在提及流查看已入库的提及与情感结果。"
    />

    <template v-else>
    <ErrorNotice v-if="store.error" :message="store.error" :retry="false" @retry="() => {}" />
    <div v-if="store.flash" class="flash rise">{{ store.flash }}</div>

    <section class="composer panel">
      <div class="panel__head">
        <span class="eyebrow">新建补采批次</span>
        <span class="mono panel__meta">brand × sources × window</span>
      </div>
      <div class="composer__grid">
        <label class="fld">
          <span class="label">品牌</span>
          <select v-model="form.brand_key" class="field" data-test="batch-brand">
            <option v-for="brand in meta.brandOptions" :key="brand.value" :value="brand.value">
              {{ brand.label }}
            </option>
          </select>
        </label>
        <fieldset class="fld fld--sources">
          <legend class="label">来源（可多选）</legend>
          <div class="source-pick">
            <button
              v-for="source in meta.sourceOptions"
              :key="source.value"
              type="button"
              class="chip"
              :class="{ 'is-on': form.source_codes.includes(source.value) }"
              :data-test="`pick-${source.value}`"
              @click="toggleSource(source.value)"
            >
              {{ source.label }}
            </button>
          </div>
        </fieldset>
        <label class="fld">
          <span class="label">开始时间</span>
          <input v-model="form.window_start" type="datetime-local" step="3600" class="field" data-test="window-start" />
        </label>
        <label class="fld">
          <span class="label">结束时间</span>
          <input v-model="form.window_end" type="datetime-local" step="3600" class="field" data-test="window-end" />
        </label>
      </div>
      <div class="composer__foot">
        <span class="composer__hint mono">单次跨度 ≤ 30 天 · 窗口左闭右开</span>
        <button class="btn btn--amber" :disabled="store.busy || !canCreate" data-test="create-batch" @click="create">
          {{ store.busy ? '提交中…' : '创建批次' }}
        </button>
      </div>
    </section>

    <section class="health panel">
      <div class="panel__head">
        <span class="eyebrow">来源连通性</span>
        <span class="mono panel__meta">outage switch（演示中断/恢复）</span>
      </div>
      <div class="health__row">
        <div v-for="item in store.sourceHealth" :key="item.code" class="health__item">
          <span class="dot" :class="{ 'dot--off': !item.online }" />
          <span class="health__name">{{ sourceLabel(item.code) }}</span>
          <span class="mono health__state" :class="{ 'is-off': !item.online }">
            {{ item.online ? '在线' : '中断' }}
          </span>
          <button
            v-if="item.online"
            class="btn btn--neg btn--mini"
            :disabled="store.busy"
            :data-test="`outage-${item.code}`"
            @click="store.toggleOutage(item.code, false, 'manual outage')"
          >
            模拟中断
          </button>
          <button
            v-else
            class="btn btn--mini"
            :disabled="store.busy"
            :data-test="`recover-${item.code}`"
            @click="store.toggleOutage(item.code, true)"
          >
            恢复
          </button>
        </div>
      </div>
    </section>

    <div class="layout">
      <section class="batch-list panel">
        <div class="panel__head">
          <span class="eyebrow">批次清单</span>
          <button class="btn btn--quiet btn--mini" :disabled="store.loading" data-test="refresh-batches" @click="store.loadList()">
            刷新
          </button>
        </div>
        <div v-if="!store.list.length" class="panel__empty">还没有补采批次，先在上方创建一个。</div>
        <button
          v-for="batch in store.list"
          :key="batch.id"
          class="batch-card"
          :class="{ 'is-on': store.current?.id === batch.id }"
          :data-test="`batch-${batch.batch_no}`"
          @click="selectBatch(batch.id)"
        >
          <div class="batch-card__top">
            <span class="mono batch-card__no">{{ batch.batch_no }}</span>
            <StatusSeal :label="batch.status_label" :tone="sealTone(batch.status)" />
          </div>
          <div class="batch-card__brand">{{ batch.brand_label }}</div>
          <div class="batch-card__window mono">{{ windowText(batch) }}</div>
          <div class="batch-card__counts mono">
            <span>待 {{ batch.counts.pending }}</span>
            <span class="pos">入 {{ batch.counts.inserted }}</span>
            <span>重 {{ batch.counts.duplicate }}</span>
            <span class="neg">失 {{ batch.counts.failed }}</span>
          </div>
        </button>
      </section>

      <section v-if="current" class="detail panel rise" data-test="batch-detail">
        <div class="detail__head">
          <div>
            <div class="eyebrow">{{ current.brand_label }} · {{ current.batch_no }}</div>
            <h2 class="detail__title">批次回看</h2>
          </div>
          <div class="detail__actions">
            <button
              v-if="current.status !== 'completed'"
              class="btn btn--amber"
              :disabled="store.busy"
              data-test="run-batch"
              @click="run"
            >
              {{ actionLabel }}
            </button>
            <button
              v-else
              class="btn"
              :disabled="store.busy"
              data-test="rerun-batch"
              @click="run"
            >
              重复运行（幂等）
            </button>
          </div>
        </div>

        <dl class="meta-grid">
          <div><dt>时间窗口</dt><dd class="mono">{{ windowText(current) }}</dd></div>
          <div><dt>创建人</dt><dd class="mono">{{ current.created_by_email || '—' }}</dd></div>
          <div><dt>运行次数</dt><dd class="mono">{{ current.run_count }}</dd></div>
          <div>
            <dt>下游同步</dt>
            <dd class="mono">
              情感 {{ current.sentiment_synced ? '✓' : '—' }} ·
              爆发 {{ current.burst_synced ? `✓(${current.burst_events})` : '—' }}
            </dd>
          </div>
        </dl>

        <div class="counters">
          <LedCounter label="待处理" :value="current.counts.pending" tone="ink" :digits="2" />
          <LedCounter label="已入库" :value="current.counts.inserted" tone="pos" :digits="2" />
          <LedCounter label="重复" :value="current.counts.duplicate" tone="amber" :digits="2" />
          <LedCounter label="失败" :value="current.counts.failed" tone="neg" :digits="2" />
        </div>

        <div v-if="current.last_error" class="error-line mono">{{ current.last_error }}</div>

        <div class="panel__head section-title">
          <span class="eyebrow">逐源处理结果</span>
          <span class="mono panel__meta">断点续跑的最小单元</span>
        </div>
        <div class="source-table" role="table">
          <div class="source-row source-row--head" role="row">
            <span>来源</span><span>状态</span><span>待处理</span><span>已入库</span>
            <span>重复</span><span>失败</span><span>尝试</span>
          </div>
          <button
            v-for="src in current.sources"
            :key="src.id"
            class="source-row"
            :class="{ 'is-on': sourceFilter === src.source_code }"
            role="row"
            :data-test="`src-row-${src.source_code}`"
            @click="filterBySource(src.source_code)"
          >
            <span class="source-row__name">{{ src.source_label }}</span>
            <span><StatusSeal :label="src.status_label" :tone="sourceSealTone(src.status)" /></span>
            <span class="mono">{{ src.counts.pending }}</span>
            <span class="mono pos">{{ src.counts.inserted }}</span>
            <span class="mono">{{ src.counts.duplicate }}</span>
            <span class="mono neg">{{ src.counts.failed }}</span>
            <span class="mono">{{ src.attempts }}</span>
          </button>
        </div>
        <p v-if="store.hasFailed" class="retry-hint">
          存在失败来源：先在「来源连通性」恢复对应来源，再点
          <em>{{ actionLabel }}</em>，已成功来源不会重放。
        </p>

        <div class="panel__head section-title">
          <span class="eyebrow">台账明细（页面数字的事实源）</span>
          <span class="mono panel__meta">{{ store.itemsTotal }} 条</span>
        </div>
        <div class="item-filters">
          <button class="chip" :class="{ 'is-on': !itemFilter }" @click="filterItems('')">全部</button>
          <button
            v-for="opt in itemStatusOptions"
            :key="opt.value"
            class="chip"
            :class="{ 'is-on': itemFilter === opt.value }"
            @click="filterItems(opt.value)"
          >
            {{ opt.label }}
          </button>
          <button v-if="sourceFilter" class="chip chip--clear" @click="clearSourceFilter">
            来源筛选：{{ sourceLabel(sourceFilter) }} ✕
          </button>
        </div>

        <div v-if="!store.items.length" class="panel__empty">当前筛选下没有台账条目。</div>
        <ul v-else class="ledger">
          <li v-for="item in store.items" :key="item.id" class="ledger__item" :data-test="`item-${item.status}`">
            <div class="ledger__main">
              <span class="ledger__title">{{ item.title }}</span>
              <span class="mono ledger__ext">{{ item.external_id }}</span>
            </div>
            <div class="ledger__side">
              <span class="ledger__meta mono">{{ item.source_label }} · {{ timeHM(item.published_at) }}</span>
              <StatusSeal :label="item.status_label" :tone="itemSealTone(item.status)" />
            </div>
            <RouterLink
              v-if="item.mention_id"
              :to="`/mentions/${item.mention_id}`"
              class="ledger__link mono"
            >
              查看提及 →
            </RouterLink>
            <span v-else-if="item.error_message" class="ledger__err mono">{{ item.error_message }}</span>
          </li>
        </ul>

        <div v-if="recon" class="recon">
          <div class="panel__head section-title">
            <span class="eyebrow">对账</span>
            <span class="mono panel__meta">台账 vs 入库明细</span>
          </div>
          <div class="recon__grid mono">
            <span>台账已入库 <b>{{ recon.ledger.inserted }}</b></span>
            <span>mentions 表 <b>{{ recon.mentions_in_db }}</b></span>
            <span>已打情感分 <b>{{ recon.sentiment_scored_in_db }}</b></span>
            <span :class="{ 'recon--ok': recon.matched, 'recon--bad': !recon.matched }">
              {{ recon.matched ? '✓ 对得上' : '✗ 不一致' }}
            </span>
          </div>
        </div>
      </section>

      <section v-else class="detail panel detail--placeholder">
        <EmptyState
          title="选择左侧批次查看详情"
          description="这里会展示逐源处理结果、待处理 / 已入库 / 重复 / 失败计数，以及可与入库明细对账的台账。"
        />
      </section>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import EmptyState from '../components/common/EmptyState.vue'
import LedCounter from '../components/common/LedCounter.vue'
import StatusSeal from '../components/common/StatusSeal.vue'
import { useMetaStore } from '../stores/metaStore'
import { useAuthStore } from '../stores/authStore'
import { useCollectBatchStore } from '../stores/collectBatchStore'
import { timeHM } from '../utils/format'
import type {
  CollectBatch,
  CollectBatchStatus,
  CollectItemStatus,
  CollectSourceStatus,
  SourceCode,
} from '../types/domain'

const meta = useMetaStore()
const auth = useAuthStore()
const store = useCollectBatchStore()

// datetime-local 不带时区：用上海时区字符串提交，后端按 +08:00 解析
function toLocalInput(d: Date): string {
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`
}
const defaultStart = new Date()
defaultStart.setDate(defaultStart.getDate() - 7)
defaultStart.setHours(0, 0, 0, 0)
const defaultEnd = new Date()
defaultEnd.setHours(23, 0, 0, 0)

const form = reactive({
  brand_key: 'coffee',
  source_codes: meta.sourceOptions.map((s) => s.value),
  window_start: toLocalInput(defaultStart),
  window_end: toLocalInput(defaultEnd),
})

const itemFilter = ref<'' | CollectItemStatus>('')
const sourceFilter = ref<'' | SourceCode>('')

const itemStatusOptions: { value: CollectItemStatus; label: string }[] = [
  { value: 'inserted', label: '已入库' },
  { value: 'duplicate', label: '重复' },
  { value: 'failed', label: '失败' },
  { value: 'skipped', label: '不适用' },
  { value: 'pending', label: '待处理' },
]

const current = computed(() => store.current)
const recon = computed(() => store.reconciliation)
const canRun = computed(() => auth.can('collect:run'))
const canCreate = computed(() => form.source_codes.length > 0 && !!form.window_start && !!form.window_end)
const actionLabel = computed(() => (store.hasFailed ? '重试失败来源' : '从断点续跑'))

function sourceLabel(code: SourceCode | ''): string {
  return code ? meta.sourceLabel(code) : ''
}

function toggleSource(code: SourceCode) {
  const idx = form.source_codes.indexOf(code)
  if (idx >= 0) form.source_codes.splice(idx, 1)
  else form.source_codes.push(code)
}

function withOffset(isoLocal: string): string {
  // datetime-local 是上海本地时间，补 +08:00 偏移
  return isoLocal.length === 16 ? `${isoLocal}:00+08:00` : isoLocal
}

async function create() {
  const created = await store.create({
    brand_key: form.brand_key,
    source_codes: [...form.source_codes],
    window_start: withOffset(form.window_start),
    window_end: withOffset(form.window_end),
  })
  sourceFilter.value = ''
  itemFilter.value = ''
  await store.loadDetail(created.id)
}

async function run() {
  if (!current.value) return
  await store.run(current.value.id)
}

async function selectBatch(id: string) {
  sourceFilter.value = ''
  itemFilter.value = ''
  await store.loadDetail(id)
}

async function filterBySource(code: SourceCode) {
  sourceFilter.value = sourceFilter.value === code ? '' : code
  await reloadItems()
}

function clearSourceFilter() {
  sourceFilter.value = ''
  void reloadItems()
}

async function filterItems(status: '' | CollectItemStatus) {
  itemFilter.value = status
  await reloadItems()
}

async function reloadItems() {
  if (!current.value) return
  await store.loadItems(current.value.id, {
    source_code: sourceFilter.value || undefined,
    status: itemFilter.value || undefined,
    limit: 100,
    offset: 0,
  })
}

function windowText(batch: CollectBatch): string {
  return `${batch.window_start.slice(0, 16).replace('T', ' ')} → ${batch.window_end
    .slice(0, 16)
    .replace('T', ' ')}`
}

function sealTone(status: CollectBatchStatus): 'open' | 'claimed' | 'handled' | 'dismissed' | 'ink' {
  if (status === 'partial') return 'open'
  if (status === 'completed') return 'handled'
  if (status === 'running') return 'claimed'
  return 'ink'
}
function sourceSealTone(status: CollectSourceStatus): 'open' | 'claimed' | 'handled' | 'dismissed' | 'ink' {
  if (status === 'failed') return 'open'
  if (status === 'success') return 'handled'
  if (status === 'running') return 'claimed'
  return 'dismissed'
}
function itemSealTone(status: CollectItemStatus): 'open' | 'claimed' | 'handled' | 'dismissed' | 'ink' {
  if (status === 'failed') return 'open'
  if (status === 'inserted') return 'handled'
  if (status === 'duplicate') return 'claimed'
  if (status === 'pending') return 'dismissed'
  return 'ink'
}

onMounted(async () => {
  if (!canRun.value) return
  await Promise.all([store.loadList(), store.loadHealth()])
})
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.flash {
  font-size: 11.5px;
  color: var(--amber);
  border-left: 2px solid var(--amber);
  padding: 2px 0 2px 9px;
}
.panel {
  border: 1px solid var(--rule);
  background: color-mix(in oklch, var(--ground-2) 70%, var(--ground));
  padding: 14px 16px;
}
.panel__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 10px;
}
.panel__meta {
  font-size: 9px;
  color: var(--ink-faint);
}
.panel__empty {
  font-size: 11.5px;
  color: var(--ink-faint);
  padding: 12px 2px;
}
.section-title {
  margin-top: 18px;
  border-top: 1px solid var(--rule-soft);
  padding-top: 12px;
}
.composer__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.fld {
  display: flex;
  flex-direction: column;
  gap: 5px;
  border: 0;
  padding: 0;
  margin: 0;
  min-width: 0;
}
.fld--sources {
  grid-column: span 1;
}
.source-pick {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.composer__foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}
.composer__hint {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.health__row {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
}
.health__item {
  display: flex;
  align-items: center;
  gap: 7px;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--pos);
}
.dot--off {
  background: var(--neg);
}
.health__name {
  font-size: 12px;
}
.health__state {
  font-size: 10px;
  color: var(--pos);
}
.health__state.is-off {
  color: var(--neg);
}
.btn--mini {
  padding: 2px 8px;
  font-size: 9px;
}
.layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
.batch-list {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.batch-card {
  text-align: left;
  background: transparent;
  border: 1px solid var(--rule-soft);
  padding: 10px 11px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: border-color 150ms var(--ease), background-color 150ms var(--ease);
}
.batch-card:hover {
  border-color: var(--rule-bright);
}
.batch-card.is-on {
  border-color: var(--amber);
  background: color-mix(in oklch, var(--amber) 10%, var(--ground));
}
.batch-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.batch-card__no {
  font-size: 11px;
  color: var(--amber);
}
.batch-card__brand {
  font-size: 13px;
}
.batch-card__window {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.batch-card__counts {
  display: flex;
  gap: 9px;
  font-size: 10.5px;
  color: var(--ink-soft);
}
.pos {
  color: var(--pos);
}
.neg {
  color: var(--neg);
}
.detail__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.detail__title {
  font-size: 17px;
  font-weight: 500;
  margin-top: 2px;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 18px;
  margin: 14px 0 4px;
}
.meta-grid div {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid var(--rule-soft);
  padding-bottom: 4px;
}
.meta-grid dt {
  font-size: 10px;
  color: var(--ink-faint);
}
.meta-grid dd {
  margin: 0;
  font-size: 11px;
}
.counters {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid var(--rule-soft);
  margin-top: 12px;
}
.error-line {
  margin-top: 10px;
  font-size: 10px;
  color: var(--neg);
  border: 1px solid color-mix(in oklch, var(--neg) 45%, transparent);
  padding: 6px 8px;
  word-break: break-all;
}
.source-table {
  border: 1px solid var(--rule-soft);
}
.source-row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) repeat(6, minmax(0, 1fr));
  gap: 6px;
  align-items: center;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--rule-soft);
  padding: 8px 10px;
  cursor: pointer;
  font-size: 11.5px;
}
.source-row:last-child {
  border-bottom: 0;
}
.source-row--head {
  cursor: default;
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--ink-faint);
  background: var(--ground-3);
}
.source-row:not(.source-row--head):hover {
  background: var(--ground-3);
}
.source-row.is-on {
  background: color-mix(in oklch, var(--amber) 12%, var(--ground));
}
.source-row__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.retry-hint {
  margin-top: 10px;
  font-size: 11px;
  color: var(--amber);
}
.retry-hint em {
  font-style: normal;
  border: 1px solid var(--amber-dim);
  padding: 0 5px;
}
.item-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.chip--clear {
  border-color: var(--amber-dim);
  color: var(--amber);
}
.ledger {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.ledger__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 14px;
  padding: 9px 2px;
  border-bottom: 1px solid var(--rule-soft);
}
.ledger__main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.ledger__title {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ledger__ext {
  font-size: 9px;
  color: var(--ink-faint);
}
.ledger__side {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ledger__meta {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.ledger__link {
  grid-column: 1 / -1;
  font-size: 10px;
}
.ledger__err {
  grid-column: 1 / -1;
  font-size: 9.5px;
  color: var(--neg);
}
.recon__grid {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  font-size: 11px;
  color: var(--ink-soft);
}
.recon--ok {
  color: var(--pos);
}
.recon--bad {
  color: var(--neg);
}
.detail--placeholder {
  min-height: 240px;
  display: flex;
  align-items: center;
}
@media (max-width: 1080px) {
  .composer__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 720px) {
  .composer__grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .counters {
    grid-template-columns: repeat(2, 1fr);
  }
  .source-row {
    grid-template-columns: minmax(0, 1.4fr) repeat(3, minmax(0, 1fr));
  }
}
</style>
