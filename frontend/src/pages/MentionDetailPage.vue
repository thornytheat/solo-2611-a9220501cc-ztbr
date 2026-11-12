<template>
  <div class="page">
    <div class="back">
      <RouterLink to="/mentions" class="back__link mono">← 返回提及流</RouterLink>
      <span class="back__crumb mono">{{ detail?.group_name ?? '—' }} · {{ detail?.source_label ?? '—' }}</span>
    </div>

    <ErrorNotice v-if="store.error" :message="store.error" @retry="reload" />

    <div v-if="!detail && store.loading" class="loading mono">正在读取提及与情感证据…</div>

    <template v-if="detail">
      <header class="head rise">
        <div class="head__main">
          <div class="head__meta">
            <SourceTag :code="detail.source_code" :label="detail.source_label" />
            <span class="head__dot">·</span>
            <span class="mono">{{ dateTime(detail.published_at) }}</span>
            <span class="head__dot">·</span>
            <span>{{ detail.author }}</span>
            <span class="head__dot">·</span>
            <span class="mono">互动 {{ detail.engagement }}</span>
            <span class="head__dot">·</span>
            <span class="mono">{{ detail.brand_label }}</span>
          </div>
          <h1 class="head__title">{{ detail.title }}</h1>
          <div class="head__tags">
            <SentimentChip :label="detail.sentiment.final_label" :score="detail.sentiment.score" />
            <StatusSeal :label="detail.sentiment.review_status_text" :tone="sealTone" />
            <span v-if="detail.sentiment.reviewed_at" class="head__reviewed mono">
              复核于 {{ dateTime(detail.sentiment.reviewed_at) }} · {{ detail.sentiment.reviewer_email }}
            </span>
            <a :href="detail.url" class="head__link mono" target="_blank" rel="noreferrer">原始链接 ↗</a>
          </div>
        </div>
        <div class="head__gauge">
          <ScoreGauge
            :score="detail.sentiment.score"
            :label="detail.sentiment.final_label"
            :confidence="detail.sentiment.confidence"
            :threshold="meta.thresholds.sentiment_neg ? Math.abs(meta.thresholds.sentiment_neg) : 0.2"
          />
        </div>
      </header>

      <div class="grid">
        <section class="col-main">
          <article class="evidence">
            <div class="evidence__cap">
              <span class="eyebrow">正文 · 情感证据词高亮</span>
              <span class="mono evidence__chars">{{ detail.body.length }} 字</span>
            </div>
            <EvidenceText :body="detail.body" :hits="detail.sentiment.hits" />
          </article>

          <HitTable
            :hits="detail.sentiment.hits"
            :positive="detail.sentiment.positive_count"
            :negative="detail.sentiment.negative_count"
            :negated="detail.sentiment.negation_count"
            :degree="detail.sentiment.degree_count"
            :rhetoric="detail.sentiment.rhetoric_count"
          />

          <section class="block">
            <div class="block__cap">
              <span class="eyebrow">同事件关联（同组 ±2 小时）</span>
              <span class="mono block__meta">{{ detail.related.length }} 条</span>
            </div>
            <ul v-if="detail.related.length" class="related">
              <li v-for="item in detail.related" :key="item.id" class="related__item">
                <RouterLink :to="`/mentions/${item.id}`" class="related__link">
                  <span class="mono related__score" :class="`is-${item.label}`">{{ item.score.toFixed(2) }}</span>
                  <span class="related__title">{{ item.title }}</span>
                  <span class="mono related__meta">{{ timeHM(item.published_at) }} · {{ item.source_code }}</span>
                </RouterLink>
              </li>
            </ul>
            <p v-else class="block__empty">该时间窗内没有同组其他提及。</p>
          </section>

          <section v-if="detail.alerts.length" class="block">
            <div class="block__cap"><span class="eyebrow">命中的爆发窗口</span></div>
            <ul class="alerts">
              <li v-for="alert in detail.alerts" :key="alert.id" class="alerts__item">
                <LevelTag :level="alert.level" />
                <span class="mono alerts__z">z={{ alert.z_score.toFixed(2) }}</span>
                <span class="mono alerts__meta">{{ dateTime(alert.window_start) }} · 量 {{ alert.count }} · {{ alert.status }}</span>
                <RouterLink to="/bursts" class="alerts__link mono">看板 →</RouterLink>
              </li>
            </ul>
          </section>
        </section>

        <aside class="col-side">
          <section class="panel">
            <div class="panel__head">
              <span class="eyebrow">人工复核</span>
              <span class="mono panel__meta">{{ detail.sentiment.review_status_text }}</span>
            </div>
            <template v-if="!reviewable">
              <p class="panel__note">
                该条已完成复核（{{ detail.sentiment.review_status_text }}），
                <span v-if="detail.sentiment.review_note">备注：{{ detail.sentiment.review_note }}</span>
                <span v-else>无备注。</span>
              </p>
            </template>
            <template v-else-if="!auth.can('mentions:review')">
              <p class="panel__note">当前角色（{{ roleLabel }}）只能阅读，不能改判情感。切到分析师或总监账号可以复核。</p>
            </template>
            <template v-else>
              <p class="panel__note">机器判定：{{ SENTIMENT_LABELS[detail.sentiment.label] }}（{{ detail.sentiment.score.toFixed(3) }}）。改判会记入审计日志。</p>
              <div class="radio-row">
                <button
                  v-for="option in labelOptions"
                  :key="option.value"
                  class="radio"
                  :class="{ 'is-on': reviewLabel === option.value, [`is-${option.value}`]: true }"
                  :data-test="`review-${option.value}`"
                  @click="reviewLabel = option.value"
                >{{ option.label }}</button>
              </div>
              <textarea
                v-model="reviewNote"
                class="field review-note"
                rows="3"
                placeholder="复核依据，例如：通报体报道，企业已回应，非消费者体验负面"
                data-test="review-note"
              />
              <button class="btn btn--amber review-submit" :disabled="submitting" data-test="review-submit" @click="submitReview">
                {{ submitting ? '提交中…' : '提交复核' }}
              </button>
              <p v-if="reviewError" class="panel__error">{{ reviewError }}</p>
              <p v-if="reviewFlash" class="panel__flash">{{ reviewFlash }}</p>
            </template>
          </section>

          <section class="panel">
            <div class="panel__head"><span class="eyebrow">打分口径</span></div>
            <dl class="kv">
              <div><dt>机器标签</dt><dd>{{ SENTIMENT_LABELS[detail.sentiment.label] }}</dd></div>
              <div><dt>最终标签</dt><dd>{{ SENTIMENT_LABELS[detail.sentiment.final_label] }}</dd></div>
              <div><dt>情感分</dt><dd class="mono">{{ detail.sentiment.score.toFixed(4) }}</dd></div>
              <div><dt>置信度</dt><dd class="mono">{{ (detail.sentiment.confidence * 100).toFixed(0) }}%</dd></div>
              <div><dt>正 / 负 词</dt><dd class="mono">{{ detail.sentiment.positive_count }} / {{ detail.sentiment.negative_count }}</dd></div>
              <div><dt>否定 / 程度</dt><dd class="mono">{{ detail.sentiment.negation_count }} / {{ detail.sentiment.degree_count }}</dd></div>
              <div><dt>感叹 / 反问</dt><dd class="mono">{{ detail.sentiment.exclaim_count }} / {{ detail.sentiment.rhetoric_count }}</dd></div>
              <div><dt>算法版本</dt><dd class="mono">{{ detail.sentiment.algorithm_version }}</dd></div>
            </dl>
          </section>

          <section class="panel">
            <div class="panel__head">
              <span class="eyebrow">所属关键词组</span>
              <span class="mono panel__meta">z&gt;{{ detail.group.z_threshold }}</span>
            </div>
            <div class="chipset">
              <span class="label">主词</span>
              <span v-for="word in detail.group.keywords" :key="word" class="mini">{{ word }}</span>
            </div>
            <div class="chipset">
              <span class="label">同义</span>
              <span v-for="word in detail.group.synonyms" :key="word" class="mini mini--syn">{{ word }}</span>
            </div>
            <div class="chipset">
              <span class="label">排除</span>
              <span v-for="word in detail.group.excludes" :key="word" class="mini mini--ex">{{ word }}</span>
            </div>
          </section>

          <section v-if="detail.audit.length" class="panel">
            <div class="panel__head"><span class="eyebrow">审计</span></div>
            <ul class="audit">
              <li v-for="entry in detail.audit" :key="entry.id" class="audit__item">
                <span class="mono audit__time">{{ dateTime(entry.created_at) }}</span>
                <span class="audit__action">{{ entry.action }}</span>
                <span class="mono audit__who">{{ entry.actor_email }}</span>
              </li>
            </ul>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import SentimentChip from '../components/common/SentimentChip.vue'
import SourceTag from '../components/common/SourceTag.vue'
import StatusSeal from '../components/common/StatusSeal.vue'
import LevelTag from '../components/common/LevelTag.vue'
import ScoreGauge from '../components/domain/ScoreGauge.vue'
import EvidenceText from '../components/domain/EvidenceText.vue'
import HitTable from '../components/domain/HitTable.vue'
import { useMentionStore } from '../stores/mentionStore'
import { useMetaStore } from '../stores/metaStore'
import { useAuthStore } from '../stores/authStore'
import { SENTIMENT_LABELS } from '../constants/enums'
import { ROLE_LABELS } from '../constants/roles'
import { dateTime, timeHM } from '../utils/format'

const route = useRoute()
const store = useMentionStore()
const meta = useMetaStore()
const auth = useAuthStore()

const detail = computed(() => store.detail)
const roleLabel = computed(() => ROLE_LABELS[auth.role])
const labelOptions = [
  { value: 'neg', label: '负面' },
  { value: 'neu', label: '中性' },
  { value: 'pos', label: '正面' },
]
const reviewLabel = ref('neu')
const reviewNote = ref('')
const submitting = ref(false)
const reviewError = ref('')
const reviewFlash = ref('')

const reviewable = computed(() => {
  const status = detail.value?.sentiment.review_status
  return status !== 'confirmed' && status !== 'corrected'
})
const sealTone = computed(() => {
  const map: Record<string, 'open' | 'claimed' | 'handled' | 'dismissed' | 'ink'> = {
    auto: 'ink',
    pending: 'open',
    confirmed: 'handled',
    corrected: 'claimed',
  }
  return map[detail.value?.sentiment.review_status ?? 'auto'] ?? 'ink'
})

async function reload() {
  const id = String(route.params.id)
  const loaded = await store.loadDetail(id)
  if (loaded) {
    reviewLabel.value = loaded.sentiment.final_label
    reviewNote.value = loaded.sentiment.review_note ?? ''
  }
}

async function submitReview() {
  if (!detail.value) return
  submitting.value = true
  reviewError.value = ''
  reviewFlash.value = ''
  try {
    const updated = await store.submitReview(detail.value.id, reviewLabel.value, reviewNote.value)
    reviewFlash.value = `已提交：${SENTIMENT_LABELS[updated.sentiment.final_label]}（${updated.sentiment.review_status_text}）`
  } catch (error) {
    reviewError.value = (error as { message?: string }).message ?? '复核提交失败'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await meta.load()
  await reload()
})
watch(() => route.params.id, reload)
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.back {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.back__link {
  font-size: 10px;
  letter-spacing: 0.08em;
}
.back__crumb {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.loading {
  font-size: 12px;
  color: var(--ink-faint);
  padding: 30px 0;
}
.head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 24px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--rule);
}
.head__meta {
  display: flex;
  align-items: baseline;
  gap: 7px;
  flex-wrap: wrap;
  font-size: 10px;
  color: var(--ink-faint);
}
.head__dot {
  color: var(--rule);
}
.head__title {
  font-size: clamp(18px, 2.2vw, 25px);
  font-weight: 500;
  line-height: 1.35;
  letter-spacing: -0.015em;
  margin-top: 6px;
}
.head__tags {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
  margin-top: 9px;
}
.head__reviewed,
.head__link {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 24px;
  align-items: start;
}
.evidence {
  border: 1px solid var(--rule-soft);
  background: color-mix(in oklch, var(--ground-2) 45%, var(--ground));
  padding: 12px 16px 14px;
}
.evidence__cap {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--rule-soft);
  margin-bottom: 10px;
}
.evidence__chars {
  font-size: 9px;
  color: var(--ink-faint);
}
.block {
  margin-top: 18px;
}
.block__cap {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid var(--rule);
  padding-bottom: 5px;
  margin-bottom: 6px;
}
.block__meta {
  font-size: 9px;
  color: var(--ink-faint);
}
.block__empty {
  font-size: 11px;
  color: var(--ink-faint);
}
.related {
  list-style: none;
  margin: 0;
  padding: 0;
}
.related__item {
  border-bottom: 1px solid var(--rule-soft);
}
.related__link {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 1px 8px;
  padding: 6px 0;
  color: var(--ink);
}
.related__link:hover {
  color: var(--amber);
  text-decoration: none;
}
.related__score {
  font-size: 11px;
  color: var(--ink-faint);
}
.related__score.is-neg {
  color: var(--neg);
}
.related__score.is-pos {
  color: var(--pos);
}
.related__title {
  font-size: 11.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.related__meta {
  grid-column: 2;
  font-size: 9px;
  color: var(--ink-faint);
}
.alerts {
  list-style: none;
  margin: 0;
  padding: 0;
}
.alerts__item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 0;
  border-bottom: 1px solid var(--rule-soft);
  flex-wrap: wrap;
}
.alerts__z {
  font-size: 11px;
  color: var(--critical);
}
.alerts__meta {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.alerts__link {
  margin-left: auto;
  font-size: 9.5px;
}
.col-side {
  display: flex;
  flex-direction: column;
  gap: 16px;
  border-left: 1px solid var(--rule-soft);
  padding-left: 18px;
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
.panel__note {
  font-size: 11px;
  color: var(--ink-soft);
  line-height: 1.7;
}
.panel__error {
  font-size: 10.5px;
  color: var(--neg);
  margin-top: 6px;
}
.panel__flash {
  font-size: 10.5px;
  color: var(--amber);
  margin-top: 6px;
}
.radio-row {
  display: flex;
  gap: 4px;
  margin: 10px 0 8px;
}
.radio {
  flex: 1;
  background: transparent;
  border: 1px solid var(--rule-soft);
  color: var(--ink-soft);
  font-size: 11px;
  padding: 5px 0;
  cursor: pointer;
}
.radio:hover {
  border-color: var(--rule-bright);
}
.radio.is-on.is-neg {
  border-color: var(--neg);
  color: var(--neg);
}
.radio.is-on.is-neu {
  border-color: var(--neu);
  color: var(--ink);
}
.radio.is-on.is-pos {
  border-color: var(--pos);
  color: var(--pos);
}
.review-note {
  resize: vertical;
  font-size: 11px;
}
.review-submit {
  margin-top: 8px;
  width: 100%;
  justify-content: center;
}
.kv {
  margin: 0;
  display: flex;
  flex-direction: column;
}
.kv div {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 3px 0;
  border-bottom: 1px solid color-mix(in oklch, var(--rule-soft) 50%, transparent);
}
.kv dt {
  font-size: 10.5px;
  color: var(--ink-faint);
}
.kv dd {
  margin: 0;
  font-size: 11.5px;
  color: var(--ink);
}
.chipset {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: baseline;
  margin-bottom: 6px;
}
.chipset .label {
  width: 34px;
  flex-shrink: 0;
}
.mini {
  font-size: 9.5px;
  border: 1px solid var(--rule-soft);
  padding: 0 5px;
  color: var(--ink-soft);
}
.mini--syn {
  border-color: color-mix(in oklch, var(--amber-dim) 60%, var(--ground));
  color: var(--amber-dim);
}
.mini--ex {
  color: var(--ink-faint);
  text-decoration: line-through;
}
.audit {
  list-style: none;
  margin: 0;
  padding: 0;
}
.audit__item {
  display: grid;
  grid-template-columns: 80px minmax(0, 1fr);
  gap: 0 6px;
  padding: 3px 0;
  border-bottom: 1px solid color-mix(in oklch, var(--rule-soft) 45%, transparent);
}
.audit__time {
  font-size: 9px;
  color: var(--ink-faint);
}
.audit__action {
  font-size: 10.5px;
  color: var(--ink-soft);
}
.audit__who {
  grid-column: 2;
  font-size: 8.5px;
  color: var(--ink-faint);
}
@media (max-width: 1060px) {
  .head {
    grid-template-columns: minmax(0, 1fr);
  }
  .head__gauge {
    max-width: 280px;
  }
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .col-side {
    border-left: 0;
    padding-left: 0;
    border-top: 1px solid var(--rule);
    padding-top: 14px;
  }
}
</style>
