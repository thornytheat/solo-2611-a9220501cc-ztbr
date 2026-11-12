<template>
  <div class="page">
    <PageHeader
      kicker="mention stream · 采集 → 打分 → 复核"
      title="提及流"
      :description="`${meta.groups.length} 组关键词 · ${meta.sources.length} 个来源 · 当前视图 ${store.total} 条。点击任一条进入情感证据页。`"
    >
      <template #actions>
        <button v-if="auth.can('collect:run')" class="btn" :disabled="busy !== ''" data-test="collect" @click="collect">
          {{ busy === 'collect' ? '采集中…' : '运行采集' }}
        </button>
        <button v-if="auth.can('sentiment:rescore')" class="btn" :disabled="busy !== ''" data-test="rescore" @click="rescore">
          {{ busy === 'rescore' ? '重算中…' : '重算情感' }}
        </button>
        <button v-if="auth.can('export:daily')" class="btn btn--amber" data-test="export" @click="openExport">
          导出日报
        </button>
      </template>
    </PageHeader>

    <ErrorNotice v-if="store.error" :message="store.error" @retry="reload" />
    <ErrorNotice v-if="actionError" title="动作失败" :message="actionError" :retry="false" @retry="() => {}" />

    <div v-if="flash" class="flash rise">{{ flash }}</div>

    <section class="toolbar">
      <input v-model="search" class="field toolbar__search" type="search" placeholder="搜索标题 / 正文…" data-test="search" />
      <select v-model="groupCode" class="field toolbar__select" data-test="group-filter">
        <option value="">全部关键词组</option>
        <option v-for="group in meta.groups" :key="group.code" :value="group.code">{{ group.name }}</option>
      </select>
      <select v-model="days" class="field toolbar__days" data-test="days-filter">
        <option :value="1">近 1 天</option>
        <option :value="3">近 3 天</option>
        <option :value="7">近 7 天（含基线）</option>
        <option :value="30">近 30 天</option>
      </select>
      <select v-model="sort" class="field toolbar__sort" data-test="sort">
        <option value="published_desc">时间倒序</option>
        <option value="score_asc">情感最负</option>
        <option value="score_desc">情感最正</option>
        <option value="engagement_desc">互动最高</option>
      </select>
    </section>

    <section class="filters">
      <div class="filters__row">
        <span class="eyebrow">来源</span>
        <button
          class="chip"
          :class="{ 'is-on': !sourceCode }"
          @click="setSource('')"
        >全部</button>
        <button
          v-for="source in meta.sourceOptions"
          :key="source.value"
          class="chip"
          :class="{ 'is-on': sourceCode === source.value }"
          :data-test="`source-${source.value}`"
          @click="setSource(source.value)"
        >
          {{ source.label }}
          <span class="chip__n mono">{{ facetCount('source', source.value) }}</span>
        </button>
      </div>
      <div class="filters__row">
        <span class="eyebrow">情感</span>
        <button class="chip" :class="{ 'is-on': !label }" @click="setLabel('')">全部</button>
        <button
          v-for="item in meta.sentimentOptions"
          :key="item.value"
          class="chip"
          :class="{ 'is-on': label === item.value }"
          :data-test="`label-${item.value}`"
          @click="setLabel(item.value)"
        >
          {{ item.label }}
          <span class="chip__n mono">{{ facetCount('label', item.value) }}</span>
        </button>
        <span class="filters__sep" />
        <button
          class="chip"
          :class="{ 'is-on': reviewPending }"
          data-test="pending-filter"
          @click="togglePending"
        >仅看待复核 <span class="chip__n mono">{{ pendingCount }}</span></button>
      </div>
    </section>

    <SentimentBand :points="store.band" class="band-block" />

    <div class="grid">
      <section class="stream">
        <div class="stream__head">
          <span class="eyebrow">提及 {{ store.total }} 条 · 已载入 {{ store.items.length }}</span>
          <span class="stream__neg mono">负面率 {{ pct(store.facets?.neg_rate ?? 0) }}</span>
        </div>
        <div v-if="store.loading && !store.items.length" class="skeleton">
          <div v-for="n in 5" :key="n" class="skeleton__row" />
        </div>
        <div v-else-if="!store.items.length" class="stream__empty">
          <EmptyState
            title="这一组筛选下没有提及"
            description="换一个来源或情感筛选；也可以运行一次采集把补扫窗口的条目拉进来（写库后自动打分）。"
          >
            <template #action>
              <button v-if="auth.can('collect:run')" class="btn" @click="collect">运行采集</button>
              <button class="btn btn--quiet" @click="resetFilters">清空筛选</button>
            </template>
          </EmptyState>
        </div>
        <div v-else class="stream__list">
          <MentionRow v-for="item in store.items" :key="item.id" :mention="item" />
        </div>
        <div v-if="store.items.length < store.total" class="stream__more">
          <button class="btn" :disabled="store.loading" @click="loadMore">载入更多（{{ store.total - store.items.length }}）</button>
        </div>
      </section>

      <aside class="rail">
        <div class="counters">
          <LedCounter label="提及总量" :value="summary?.total ?? store.total" tone="ink" :digits="4" />
          <LedCounter label="负面" :value="summary?.distribution.find((d) => d.value === 'neg')?.count ?? 0" tone="neg" :digits="3" />
          <LedCounter
            label="负面率"
            :value="pct(summary?.neg_rate ?? 0)"
            tone="neg"
            :hint="`各组均值 ${pct(summary?.avg_neg_rate ?? 0)}`"
          />
        </div>

        <section class="panel">
          <div class="panel__head">
            <span class="eyebrow">情感分布</span>
            <span class="mono panel__meta">{{ summary?.algorithm_version ?? 'sent-1.0.0' }}</span>
          </div>
          <MeterRows :rows="distributionRows" />
          <button class="btn btn--quiet panel__link" @click="loadSummary">刷新读数</button>
        </section>

        <section class="panel">
          <div class="panel__head">
            <span class="eyebrow">高频负面证据词</span>
            <span class="mono panel__meta">neg hits</span>
          </div>
          <div v-if="summary?.evidence_words.length" class="words">
            <span v-for="word in summary.evidence_words" :key="word.word" class="word mono">
              {{ word.word }}<em>{{ word.count }}</em>
            </span>
          </div>
          <p v-else class="panel__empty">暂无负面命中词。</p>
        </section>

        <section class="panel">
          <div class="panel__head">
            <span class="eyebrow">待复核队列</span>
            <span class="mono panel__meta">{{ store.queueTotal }} 条</span>
          </div>
          <ul v-if="store.queue.length" class="queue">
            <li v-for="item in store.queue" :key="item.id" class="queue__item">
              <RouterLink :to="`/mentions/${item.id}`" class="queue__link">
                <span class="queue__score mono">{{ item.sentiment.score.toFixed(2) }}</span>
                <span class="queue__title">{{ item.title }}</span>
                <span class="queue__meta mono">{{ item.group_name }} · {{ timeHM(item.published_at) }}</span>
              </RouterLink>
            </li>
          </ul>
          <p v-else class="panel__empty">队列已清空：所有负面提及都已人工复核。</p>
        </section>

        <section v-if="collectReport" class="panel panel--run">
          <div class="panel__head">
            <span class="eyebrow">最近一次采集</span>
            <span class="mono panel__meta">{{ collectReport.elapsed_ms }}ms</span>
          </div>
          <dl class="run">
            <div><dt>扫描</dt><dd class="mono">{{ collectReport.scanned }}</dd></div>
            <div><dt>新增</dt><dd class="mono amber">{{ collectReport.inserted }}</dd></div>
            <div><dt>重复</dt><dd class="mono">{{ collectReport.duplicates }}</dd></div>
            <div><dt>库内总量</dt><dd class="mono">{{ collectReport.total_mentions }}</dd></div>
          </dl>
          <p class="panel__note">{{ collectReport.window_note }}</p>
        </section>
      </aside>
    </div>

    <div v-if="exportOpen" class="modal" @click.self="exportOpen = false">
      <div class="modal__panel">
        <div class="modal__head">
          <div>
            <div class="eyebrow">daily report · markdown</div>
            <h3 class="modal__title">{{ report?.filename ?? '日报预览' }}</h3>
          </div>
          <div class="modal__actions">
            <button class="btn" :disabled="!report" @click="download">下载 .md</button>
            <button class="btn btn--quiet" @click="exportOpen = false">关闭</button>
          </div>
        </div>
        <pre v-if="report" class="modal__body">{{ report.markdown }}</pre>
        <p v-else class="modal__body">正在生成…</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import EmptyState from '../components/common/EmptyState.vue'
import LedCounter from '../components/common/LedCounter.vue'
import SentimentBand from '../components/domain/SentimentBand.vue'
import MentionRow from '../components/domain/MentionRow.vue'
import MeterRows from '../components/domain/MeterRows.vue'
import { useMentionStore } from '../stores/mentionStore'
import { useMetaStore } from '../stores/metaStore'
import { useAuthStore } from '../stores/authStore'
import { fetchSummary, rescore as apiRescore } from '../api/sentiment'
import { runCollection } from '../api/collect'
import { previewDaily } from '../api/report'
import type { CollectReport, DailyReport, SentimentSummary } from '../types/domain'
import { pct, timeHM } from '../utils/format'
import { useDebounced } from '../hooks/useDebounced'
import type { Ref } from 'vue'

const store = useMentionStore()
const meta = useMetaStore()
const auth = useAuthStore()

const search = ref('')
const debouncedSearch = useDebounced(search as Ref<string>, 340)
const groupCode = ref('')
const sourceCode = ref('')
const label = ref('')
const days = ref(7)
const sort = ref('published_desc')
const reviewPending = ref(false)
const busy = ref<'' | 'collect' | 'rescore'>('')
const actionError = ref('')
const flash = ref('')

const summary = ref<SentimentSummary | null>(null)
const collectReport = ref<CollectReport | null>(null)
const exportOpen = ref(false)
const report = ref<DailyReport | null>(null)

const pendingCount = computed(() => store.facets?.review.find((item) => item.value === 'pending')?.count ?? 0)

const distributionRows = computed(() => {
  const rows = summary.value?.distribution ?? []
  const tone: Record<string, 'neg' | 'pos' | 'ink'> = { neg: 'neg', pos: 'pos', neu: 'ink' }
  return rows.map((item) => ({
    label: item.label,
    value: item.ratio,
    display: `${item.count} · ${pct(item.ratio)}`,
    tone: tone[item.value],
  }))
})

function facetCount(kind: 'source' | 'label', value: string): number {
  const buckets = kind === 'source' ? store.facets?.source : store.facets?.label
  return buckets?.find((item) => item.value === value)?.count ?? 0
}

async function reload() {
  await store.load({
    q: debouncedSearch.value,
    group_code: groupCode.value,
    source_code: sourceCode.value,
    label: label.value,
    review_status: reviewPending.value ? 'pending' : '',
    days: days.value,
    sort: sort.value,
    offset: 0,
    limit: 30,
  })
}

function setSource(value: string) {
  sourceCode.value = value
  void reload()
}
function setLabel(value: string) {
  label.value = value
  void reload()
}
function togglePending() {
  reviewPending.value = !reviewPending.value
  void reload()
}
function resetFilters() {
  search.value = ''
  groupCode.value = ''
  sourceCode.value = ''
  label.value = ''
  reviewPending.value = false
  store.resetQuery()
  void reload()
}
function loadMore() {
  void store.load({ limit: Math.min(90, (store.query.limit ?? 30) + 30) })
}

async function loadSummary() {
  try {
    summary.value = await fetchSummary()
  } catch {
    /* 侧栏读数失败不阻塞主列表 */
  }
}

async function collect() {
  busy.value = 'collect'
  actionError.value = ''
  flash.value = ''
  try {
    const result = await runCollection()
    collectReport.value = result
    flash.value = `采集完成：扫描 ${result.scanned} · 新增 ${result.inserted} · 重复 ${result.duplicates} · 库内 ${result.total_mentions}`
    await Promise.all([reload(), loadSummary(), store.loadQueue()])
    await meta.load(true)
  } catch (error) {
    actionError.value = (error as { message?: string }).message ?? '采集失败'
  } finally {
    busy.value = ''
  }
}

async function rescore() {
  busy.value = 'rescore'
  actionError.value = ''
  try {
    const result = await apiRescore()
    flash.value = `情感重算完成：${result.scored} 条，变化 ${result.changed} 条，负面率 ${pct(result.neg_rate)}（${result.elapsed_ms}ms）`
    await Promise.all([reload(), loadSummary(), store.loadQueue()])
  } catch (error) {
    actionError.value = (error as { message?: string }).message ?? '重算失败'
  } finally {
    busy.value = ''
  }
}

async function openExport() {
  exportOpen.value = true
  report.value = null
  try {
    report.value = await previewDaily()
  } catch (error) {
    actionError.value = (error as { message?: string }).message ?? '日报生成失败'
    exportOpen.value = false
  }
}

function download() {
  if (!report.value) return
  const blob = new Blob([report.value.markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = report.value.filename
  anchor.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await meta.load()
  await Promise.all([reload(), loadSummary(), store.loadQueue()])
})
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.flash {
  font-size: 11.5px;
  color: var(--amber);
  border-left: 2px solid var(--amber);
  padding: 2px 0 2px 9px;
}
.toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 190px 130px 140px;
  gap: 8px;
}
.filters {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.filters__row {
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
.band-block {
  margin-top: 2px;
}
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 22px;
  align-items: start;
}
.stream__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 7px;
  border-bottom: 1px solid var(--rule);
}
.stream__neg {
  font-size: 10px;
  color: var(--neg);
}
.stream__list {
  border-top: 0;
}
.stream__more {
  padding: 14px 0;
  text-align: center;
}
.stream__empty {
  padding-top: 10px;
}
.skeleton {
  display: flex;
  flex-direction: column;
}
.skeleton__row {
  height: 58px;
  border-bottom: 1px solid var(--rule-soft);
  background: linear-gradient(90deg, transparent, color-mix(in oklch, var(--ground-3) 60%, transparent), transparent);
  animation: led-pulse 1.6s ease-in-out infinite;
}
.rail {
  display: flex;
  flex-direction: column;
  gap: 16px;
  border-left: 1px solid var(--rule-soft);
  padding-left: 18px;
  position: sticky;
  top: 58px;
}
.counters {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.panel {
  border-top: 1px solid var(--rule);
  padding-top: 8px;
}
.panel__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 6px;
}
.panel__meta {
  font-size: 9px;
  color: var(--ink-faint);
}
.panel__link {
  margin-top: 6px;
  padding-left: 0;
  font-size: 10px;
}
.panel__empty {
  font-size: 11px;
  color: var(--ink-faint);
  padding: 4px 0 2px;
}
.panel__note {
  font-size: 9.5px;
  color: var(--ink-faint);
  margin-top: 7px;
  line-height: 1.6;
}
.words {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.word {
  font-size: 9.5px;
  color: var(--ink-soft);
  border: 1px solid var(--rule-soft);
  padding: 1px 6px;
}
.word em {
  font-style: normal;
  color: var(--neg);
  margin-left: 4px;
  font-size: 9px;
}
.queue {
  list-style: none;
  margin: 0;
  padding: 0;
}
.queue__item {
  border-bottom: 1px solid var(--rule-soft);
}
.queue__link {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 2px 7px;
  padding: 6px 0;
  color: var(--ink);
}
.queue__link:hover {
  text-decoration: none;
  color: var(--amber);
}
.queue__score {
  font-size: 11px;
  color: var(--neg);
}
.queue__title {
  font-size: 11.5px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.queue__meta {
  grid-column: 2;
  font-size: 9px;
  color: var(--ink-faint);
}
.run {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 10px;
  margin: 0;
}
.run div {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid color-mix(in oklch, var(--rule-soft) 55%, transparent);
  padding-bottom: 2px;
}
.run dt {
  font-size: 10px;
  color: var(--ink-faint);
}
.run dd {
  margin: 0;
  font-size: 12px;
  color: var(--ink);
}
.modal {
  position: fixed;
  inset: 0;
  background: color-mix(in oklch, var(--ground) 82%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px;
  z-index: 50;
}
.modal__panel {
  width: min(880px, 100%);
  max-height: 82vh;
  display: flex;
  flex-direction: column;
  background: var(--ground-2);
  border: 1px solid var(--rule);
}
.modal__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px 16px;
  border-bottom: 1px solid var(--rule);
}
.modal__title {
  font-size: 14px;
  font-weight: 500;
  margin-top: 2px;
}
.modal__actions {
  display: flex;
  gap: 6px;
}
.modal__body {
  overflow: auto;
  margin: 0;
  padding: 16px 18px;
  font-family: var(--mono);
  font-size: 11px;
  line-height: 1.75;
  color: var(--ink-soft);
  white-space: pre-wrap;
}
@media (max-width: 1080px) {
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .rail {
    position: static;
    border-left: 0;
    padding-left: 0;
    border-top: 1px solid var(--rule);
    padding-top: 14px;
  }
  .counters {
    flex-direction: row;
  }
}
@media (max-width: 760px) {
  .toolbar {
    grid-template-columns: minmax(0, 1fr);
  }
  .counters {
    flex-wrap: wrap;
  }
}
</style>
