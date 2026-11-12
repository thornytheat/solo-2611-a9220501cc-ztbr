import { defineStore } from 'pinia'
import { fetchBootstrap, fetchDictionary } from '../api/meta'
import type { BootstrapPayload, DictionaryPayload, EnumOption } from '../types/domain'

interface MetaState {
  payload: BootstrapPayload | null
  dictionary: DictionaryPayload | null
  loading: boolean
  error: string
}

export const useMetaStore = defineStore('meta', {
  state: (): MetaState => ({ payload: null, dictionary: null, loading: false, error: '' }),
  getters: {
    org: (state) => state.payload?.org ?? { name: '', size: '', brands_served: 0, sources: 0 },
    sources: (state) => state.payload?.sources ?? [],
    brands: (state) => state.payload?.brands ?? [],
    groups: (state) => state.payload?.groups ?? [],
    thresholds: (state) => state.payload?.thresholds ?? {},
    algorithms: (state) => state.payload?.algorithms ?? null,
    counts: (state) => state.payload?.counts ?? { mentions: 0, bursts: 0, groups: 0 },
    sentimentOptions: (state): EnumOption[] => state.payload?.enums.sentiment ?? [],
    levelOptions: (state) => state.payload?.enums.burst_level ?? [],
    sourceOptions: (state) => state.payload?.enums.source ?? [],
    brandOptions: (state) => state.payload?.enums.brand ?? [],
    reviewOptions: (state) => state.payload?.enums.review_status ?? [],
    lexiconSizes: (state) => state.payload?.algorithms.sentiment.lexicon ?? {},
  },
  actions: {
    async load(force = false) {
      if (this.payload && !force) return
      this.loading = true
      this.error = ''
      try {
        this.payload = await fetchBootstrap()
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '元信息加载失败'
      } finally {
        this.loading = false
      }
    },
    async loadDictionary() {
      if (this.dictionary) return
      this.dictionary = await fetchDictionary()
    },
    sourceLabel(code: string): string {
      return this.payload?.enums.source.find((item) => item.value === code)?.label ?? code
    },
    brandLabel(key: string | null | undefined): string {
      if (!key) return '全部品牌'
      return this.payload?.enums.brand.find((item) => item.value === key)?.label ?? key
    },
  },
})
