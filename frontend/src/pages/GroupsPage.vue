<template>
  <div class="page">
    <PageHeader
      kicker="keyword groups · synonyms · excludes"
      title="关键词组与词典"
      :description="`${store.totals.groups} 组关键词覆盖 ${meta.brands.length} 个品牌；同义词扩召回，排除词去噪声。改完可先「试算召回」再保存。`"
    >
      <template #actions>
        <button v-if="canWrite" class="btn" data-test="new-group" @click="startCreate">新建组</button>
        <button v-if="canTrial" class="btn" :disabled="!form.keywordsText.trim().length" data-test="trial" @click="runTrial">试算召回</button>
        <button v-if="canWrite" class="btn btn--amber" :disabled="store.saving" data-test="save-group" @click="save">保存修改</button>
      </template>
    </PageHeader>

    <ErrorNotice v-if="store.error" :message="store.error" :retry="false" @retry="() => {}" />
    <div v-if="store.flash" class="flash rise">{{ store.flash }}</div>

    <div class="grid">
      <aside class="list">
        <div class="list__head">
          <span class="eyebrow">词组清单</span>
          <span class="mono list__meta">{{ store.enabledCount }}/{{ store.items.length }} 启用</span>
        </div>
        <button
          v-for="group in store.items"
          :key="group.id"
          class="item"
          :class="{ 'is-on': group.id === pendingId }"
          :data-test="`group-${group.code}`"
          @click="selectGroup(group.id)"
        >
          <span class="item__brand mono">{{ group.brand_label }}</span>
          <span class="item__name">{{ group.name }}</span>
          <span class="item__stats mono">
            {{ group.stats?.mentions ?? 0 }} 条 · 负 {{ pct(group.stats?.neg_rate ?? 0) }}
          </span>
          <span v-if="!group.enabled" class="item__off mono">停用</span>
        </button>
      </aside>

      <section class="editor">
        <div class="editor__head">
          <div>
            <div class="eyebrow">{{ creating ? 'new group' : `${form.brandLabel} · z>${form.z_threshold}` }}</div>
            <h2 class="editor__title">{{ creating ? '新建关键词组' : form.name || '（未命名）' }}</h2>
          </div>
          <span class="mono editor__code">{{ creating ? form.code || 'draft' : form.code }}</span>
        </div>

        <div class="form-grid">
          <label class="fld">
            <span class="label">组名</span>
            <input v-model="form.name" class="field" :disabled="!canWrite || !creating" data-test="group-name" />
          </label>
          <label class="fld">
            <span class="label">品牌</span>
            <select v-model="form.brand_key" class="field" :disabled="!canWrite || !creating">
              <option v-for="brand in meta.brands" :key="brand.key" :value="brand.key">{{ brand.name }}</option>
            </select>
          </label>
          <label v-if="creating" class="fld">
            <span class="label">编码（小写英文/短横线）</span>
            <input v-model="form.code" class="field" placeholder="coffee-newtopic" :disabled="!canWrite" />
          </label>
          <label class="fld">
            <span class="label">激活</span>
            <button
              class="toggle"
              :class="{ 'is-on': form.enabled }"
              :disabled="!canWrite"
              @click="form.enabled = !form.enabled"
            >{{ form.enabled ? '启用中' : '已停用' }}</button>
          </label>
        </div>

        <div class="tags">
          <label class="fld fld--wide">
            <span class="label">主关键词（每行一个）</span>
            <textarea v-model="form.keywordsText" class="field tags__area" rows="4" :disabled="!canWrite" data-test="keywords" />
          </label>
          <label class="fld fld--wide">
            <span class="label">同义词 / 谐音 / 品牌简写（扩召回）</span>
            <textarea v-model="form.synonymsText" class="field tags__area" rows="4" :disabled="!canWrite" data-test="synonyms" />
          </label>
          <label class="fld fld--wide">
            <span class="label">排除词（去噪声）</span>
            <textarea v-model="form.excludesText" class="field tags__area" rows="3" :disabled="!canWrite" data-test="excludes" />
          </label>
        </div>

        <div class="form-grid form-grid--tight">
          <label class="fld">
            <span class="label">z 阈值</span>
            <input v-model.number="form.z_threshold" class="field mono" type="number" step="0.1" min="1" max="8" :disabled="!canWrite" />
          </label>
          <label class="fld">
            <span class="label">最小量 x</span>
            <input v-model.number="form.min_count" class="field mono" type="number" min="1" max="50" :disabled="!canWrite" />
          </label>
          <label class="fld">
            <span class="label">优先级</span>
            <input v-model.number="form.priority" class="field mono" type="number" min="0" max="10" :disabled="!canWrite" />
          </label>
          <label class="fld fld--wide">
            <span class="label">值班备注</span>
            <input v-model="form.owner_note" class="field" :disabled="!canWrite" />
          </label>
        </div>

        <section v-if="store.trial" class="trial">
          <div class="trial__head">
            <span class="eyebrow">试算召回预览</span>
            <span class="mono trial__meta">
              扫描 {{ store.trial.scanned }} · 命中 {{ store.trial.matched }} · 保留 {{ store.trial.kept }} · 排除 {{ store.trial.excluded }}
            </span>
          </div>
          <div class="trial__bars">
            <div class="trial__bar">
              <span class="label">召回率</span>
              <span class="trial__track"><span class="trial__fill" :style="{ width: pct(store.trial.recall_rate) }" /></span>
              <span class="mono">{{ pct(store.trial.recall_rate) }}</span>
            </div>
            <div class="trial__bar">
              <span class="label">命中精度</span>
              <span class="trial__track"><span class="trial__fill trial__fill--pos" :style="{ width: pct(store.trial.precision_hint) }" /></span>
              <span class="mono">{{ pct(store.trial.precision_hint) }}</span>
            </div>
          </div>
          <ul class="trial__samples">
            <li v-for="sample in store.trial.samples" :key="sample.external_id" class="trial__sample">
              <span class="mono trial__src">{{ sample.source_code }}</span>
              <span class="trial__title">{{ sample.title }}</span>
              <span class="mono trial__hits">
                {{ [...sample.hit_keywords, ...sample.hit_synonyms].join(' / ') || '—' }}
                <em v-if="sample.hit_excludes.length">⊘ {{ sample.hit_excludes.join(' / ') }}</em>
              </span>
            </li>
          </ul>
          <p class="trial__note">{{ store.trial.corpus_note }}</p>
        </section>

        <section class="dictionary">
          <div class="dict__head">
            <span class="eyebrow">情感词典（只读 · 后端唯一事实源）</span>
            <span class="mono dict__meta">
              正 {{ dictionary?.sizes.positive ?? '—' }} · 负 {{ dictionary?.sizes.negative ?? '—' }} · 程度
              {{ dictionary?.sizes.degree ?? '—' }} · 否定 {{ dictionary?.sizes.negator ?? '—' }}
            </span>
          </div>
          <div v-if="dictionary" class="dict__cols">
            <div>
              <div class="label">正面词 top</div>
              <div class="dict__words">
                <span v-for="word in dictionary.positive.slice(0, 12)" :key="word.word" class="mini">{{ word.word }}<em>{{ word.weight }}</em></span>
              </div>
            </div>
            <div>
              <div class="label">负面词 top</div>
              <div class="dict__words">
                <span v-for="word in dictionary.negative.slice(0, 12)" :key="word.word" class="mini mini--neg">{{ word.word }}<em>{{ word.weight }}</em></span>
              </div>
            </div>
            <div>
              <div class="label">否定 / 反问</div>
              <div class="dict__words">
                <span v-for="word in dictionary.negators.slice(0, 8)" :key="word" class="mini mini--ex">{{ word }}</span>
                <span v-for="word in dictionary.rhetorical.slice(0, 4)" :key="word" class="mini mini--syn">{{ word }}</span>
              </div>
            </div>
          </div>
        </section>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import { useGroupStore } from '../stores/groupStore'
import { useMetaStore } from '../stores/metaStore'
import { useAuthStore } from '../stores/authStore'
import { fetchDictionary } from '../api/meta'
import type { DictionaryPayload } from '../types/domain'
import { pct } from '../utils/format'

const store = useGroupStore()
const meta = useMetaStore()
const auth = useAuthStore()

const canWrite = computed(() => auth.can('groups:write'))
const canTrial = computed(() => auth.can('groups:trial'))
const dictionary = ref<DictionaryPayload | null>(null)
const creating = ref(false)
const pendingId = computed(() => store.selectedId)

const form = reactive({
  code: '',
  name: '',
  brand_key: 'coffee',
  brandLabel: '',
  keywordsText: '',
  synonymsText: '',
  excludesText: '',
  enabled: true,
  priority: 5,
  z_threshold: 3,
  min_count: 5,
  owner_note: '',
})

function lines(text: string): string[] {
  return text
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function syncForm() {
  const group = store.selected
  if (!group) return
  creating.value = false
  form.code = group.code
  form.name = group.name
  form.brand_key = group.brand_key
  form.brandLabel = group.brand_label
  form.keywordsText = group.keywords.join('\n')
  form.synonymsText = group.synonyms.join('\n')
  form.excludesText = group.excludes.join('\n')
  form.enabled = group.enabled
  form.priority = group.priority
  form.z_threshold = group.z_threshold
  form.min_count = group.min_count
  form.owner_note = group.owner_note
}

function selectGroup(id: string) {
  store.select(id)
  syncForm()
}

function startCreate() {
  creating.value = true
  form.code = ''
  form.name = ''
  form.brand_key = 'coffee'
  form.brandLabel = meta.brandLabel('coffee')
  form.keywordsText = ''
  form.synonymsText = ''
  form.excludesText = ''
  form.enabled = true
  form.priority = 5
  form.z_threshold = 3
  form.min_count = 5
  form.owner_note = ''
}

async function save() {
  if (creating.value) {
    await store.create({
      code: form.code,
      name: form.name,
      brand_key: form.brand_key,
      keywords: lines(form.keywordsText),
      synonyms: lines(form.synonymsText),
      excludes: lines(form.excludesText),
      enabled: form.enabled,
      priority: form.priority,
      z_threshold: form.z_threshold,
      min_count: form.min_count,
      owner_note: form.owner_note,
    })
    creating.value = false
    syncForm()
    return
  }
  await store.save({
    name: form.name,
    keywords: lines(form.keywordsText),
    synonyms: lines(form.synonymsText),
    excludes: lines(form.excludesText),
    enabled: form.enabled,
    priority: form.priority,
    z_threshold: form.z_threshold,
    min_count: form.min_count,
    owner_note: form.owner_note,
  })
}

async function runTrial() {
  await store.trialRun({
    code: form.code || 'draft',
    keywords: lines(form.keywordsText),
    synonyms: lines(form.synonymsText),
    excludes: lines(form.excludesText),
  })
}

onMounted(async () => {
  await meta.load()
  await store.load()
  syncForm()
  try {
    dictionary.value = await fetchDictionary()
  } catch {
    dictionary.value = null
  }
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
  padding-left: 9px;
}
.grid {
  display: grid;
  grid-template-columns: 264px minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}
.list {
  border-right: 1px solid var(--rule-soft);
  padding-right: 14px;
  position: sticky;
  top: 58px;
}
.list__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--rule);
  margin-bottom: 4px;
}
.list__meta {
  font-size: 9px;
  color: var(--ink-faint);
}
.item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0 6px;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--rule-soft);
  border-left: 2px solid transparent;
  padding: 7px 6px 7px 8px;
  cursor: pointer;
  color: var(--ink);
  transition: background-color 140ms var(--ease), border-color 140ms var(--ease);
}
.item:hover {
  background: color-mix(in oklch, var(--ground-3) 55%, var(--ground));
}
.item.is-on {
  border-left-color: var(--amber);
  background: color-mix(in oklch, var(--ground-3) 80%, var(--ground));
}
.item__brand {
  grid-column: 1 / -1;
  font-size: 9px;
  color: var(--ink-faint);
}
.item__name {
  font-size: 12.5px;
}
.item__stats {
  grid-column: 1 / -1;
  font-size: 9px;
  color: var(--ink-faint);
}
.item__off {
  grid-row: 2;
  font-size: 8.5px;
  color: var(--neg);
}
.editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.editor__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--rule);
}
.editor__title {
  font-size: 21px;
  font-weight: 500;
  letter-spacing: -0.01em;
}
.editor__code {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.form-grid--tight {
  grid-template-columns: 100px 100px 100px minmax(0, 1fr);
}
.fld {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.fld--wide {
  grid-column: span 2;
}
.tags {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.tags__area {
  resize: vertical;
  font-size: 12px;
  line-height: 1.8;
}
.toggle {
  background: transparent;
  border: 1px solid var(--rule-soft);
  color: var(--ink-faint);
  font-family: var(--mono);
  font-size: 10.5px;
  padding: 7px 8px;
  cursor: pointer;
  text-align: left;
}
.toggle.is-on {
  border-color: var(--watch);
  color: var(--watch);
}
.trial {
  border: 1px solid var(--rule);
  padding: 10px 12px;
  background: color-mix(in oklch, var(--ground-2) 55%, var(--ground));
}
.trial__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 6px;
}
.trial__meta {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.trial__bars {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 8px;
}
.trial__bar {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) 52px;
  gap: 8px;
  align-items: center;
  font-size: 9.5px;
  color: var(--ink-faint);
}
.trial__track {
  height: 3px;
  background: var(--ground-4);
}
.trial__fill {
  display: block;
  height: 100%;
  background: var(--amber);
}
.trial__fill--pos {
  background: var(--watch);
}
.trial__samples {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
}
.trial__sample {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  gap: 0 8px;
  padding: 4px 0;
  border-bottom: 1px solid var(--rule-soft);
}
.trial__src {
  font-size: 9px;
  color: var(--ink-faint);
}
.trial__title {
  font-size: 11.5px;
  color: var(--ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trial__hits {
  grid-column: 2;
  font-size: 9px;
  color: var(--amber-dim);
}
.trial__hits em {
  font-style: normal;
  color: var(--neg);
  margin-left: 6px;
}
.trial__note {
  font-size: 9px;
  color: var(--ink-faint);
  margin-top: 7px;
}
.dictionary {
  border-top: 1px solid var(--rule);
  padding-top: 9px;
}
.dict__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.dict__meta {
  font-size: 9px;
  color: var(--ink-faint);
}
.dict__cols {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.dict__words {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 5px;
}
.mini {
  font-size: 9.5px;
  border: 1px solid var(--rule-soft);
  padding: 0 5px;
  color: var(--ink-soft);
}
.mini em {
  font-style: normal;
  color: var(--ink-faint);
  margin-left: 3px;
  font-size: 8.5px;
}
.mini--neg {
  border-color: color-mix(in oklch, var(--neg) 45%, var(--ground));
  color: color-mix(in oklch, var(--neg) 75%, var(--ink));
}
.mini--syn {
  border-color: var(--amber-dim);
  color: var(--amber-dim);
}
.mini--ex {
  color: var(--ink-faint);
  text-decoration: line-through;
}
@media (max-width: 1180px) {
  .form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .form-grid--tight {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .dict__cols {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 900px) {
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .list {
    border-right: 0;
    padding-right: 0;
    position: static;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 10px;
  }
  .tags {
    grid-template-columns: minmax(0, 1fr);
  }
  .fld--wide {
    grid-column: span 1;
  }
}
</style>
