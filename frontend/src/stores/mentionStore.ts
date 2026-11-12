import { defineStore } from 'pinia'
import { fetchMention, fetchMentions, fetchReviewQueue, reviewMention, type MentionQuery } from '../api/mention'
import type { MentionDetail, MentionItem, MentionListResponse } from '../types/domain'

interface MentionState {
  list: MentionListResponse | null
  detail: MentionDetail | null
  queue: MentionItem[]
  queueTotal: number
  loading: boolean
  error: string
  query: MentionQuery
}

const defaultQuery = (): MentionQuery => ({
  group_code: '',
  source_code: '',
  label: '',
  review_status: '',
  q: '',
  days: 7,
  sort: 'published_desc',
  limit: 30,
  offset: 0,
})

export const useMentionStore = defineStore('mention', {
  state: (): MentionState => ({
    list: null,
    detail: null,
    queue: [],
    queueTotal: 0,
    loading: false,
    error: '',
    query: defaultQuery(),
  }),
  getters: {
    items: (state): MentionItem[] => state.list?.items ?? [],
    total: (state): number => state.list?.total ?? 0,
    facets: (state) => state.list?.facets ?? null,
    band: (state) => state.list?.band ?? [],
  },
  actions: {
    async load(query?: MentionQuery) {
      this.loading = true
      this.error = ''
      try {
        if (query) this.query = { ...this.query, ...query }
        const params: MentionQuery = { ...this.query }
        Object.keys(params).forEach((key) => {
          const value = params[key as keyof MentionQuery]
          if (value === '' || value === null || value === undefined) delete params[key as keyof MentionQuery]
        })
        this.list = await fetchMentions(params)
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载提及失败'
      } finally {
        this.loading = false
      }
    },
    async loadDetail(id: string) {
      this.loading = true
      this.error = ''
      try {
        this.detail = await fetchMention(id)
        return this.detail
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载详情失败'
        return null
      } finally {
        this.loading = false
      }
    },
    async loadQueue(limit = 6) {
      try {
        const result = await fetchReviewQueue(limit)
        this.queue = result.items
        this.queueTotal = result.total
      } catch {
        this.queue = []
      }
    },
    async submitReview(id: string, label: string, note: string) {
      const updated = await reviewMention(id, label, note)
      this.detail = updated
      if (this.list) {
        this.list.items = this.list.items.map((item) =>
          item.id === updated.id
            ? { ...item, sentiment: { ...item.sentiment, ...updated.sentiment } }
            : item,
        )
      }
      await this.loadQueue()
      return updated
    },
    resetQuery() {
      this.query = defaultQuery()
    },
  },
})
