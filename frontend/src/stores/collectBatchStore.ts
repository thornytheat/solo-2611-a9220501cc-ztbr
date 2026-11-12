import { defineStore } from 'pinia'
import {
  createCollectBatch,
  fetchBatchItems,
  fetchBatchReconciliation,
  fetchCollectBatch,
  fetchCollectBatches,
  fetchSourceHealth,
  runCollectBatch,
  setSourceHealth,
  type BatchItemsQuery,
  type CreateBatchPayload,
} from '../api/collectBatch'
import type {
  CollectBatch,
  CollectBatchItem,
  CollectBatchReconciliation,
  SourceHealth,
} from '../types/domain'

interface CollectBatchState {
  list: CollectBatch[]
  total: number
  current: CollectBatch | null
  items: CollectBatchItem[]
  itemsTotal: number
  reconciliation: CollectBatchReconciliation | null
  sourceHealth: SourceHealth[]
  loading: boolean
  busy: boolean
  error: string
  flash: string
}

export const useCollectBatchStore = defineStore('collect-batch', {
  state: (): CollectBatchState => ({
    list: [],
    total: 0,
    current: null,
    items: [],
    itemsTotal: 0,
    reconciliation: null,
    sourceHealth: [],
    loading: false,
    busy: false,
    error: '',
    flash: '',
  }),
  getters: {
    failedSources: (state): string[] =>
      state.current?.sources.filter((s) => s.status === 'failed').map((s) => s.source_code) ?? [],
    hasFailed: (state): boolean => (state.current?.sources.some((s) => s.status === 'failed') ?? false),
    isFinished: (state): boolean =>
      state.current?.status === 'completed' || state.current?.status === 'partial',
  },
  actions: {
    async loadList() {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchCollectBatches(20, 0)
        this.list = result.items
        this.total = result.total
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '批次加载失败'
      } finally {
        this.loading = false
      }
    },
    async loadDetail(id: string) {
      this.loading = true
      this.error = ''
      try {
        this.current = await fetchCollectBatch(id)
        await Promise.all([this.loadItems(id), this.loadReconciliation(id), this.loadHealth()])
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '批次详情加载失败'
      } finally {
        this.loading = false
      }
    },
    async loadItems(id: string, query: BatchItemsQuery = { limit: 100, offset: 0 }) {
      const result = await fetchBatchItems(id, query)
      this.items = result.items
      this.itemsTotal = result.total
    },
    async loadReconciliation(id: string) {
      this.reconciliation = await fetchBatchReconciliation(id)
    },
    async loadHealth() {
      const result = await fetchSourceHealth()
      this.sourceHealth = result.items
    },
    async create(payload: CreateBatchPayload) {
      this.busy = true
      this.error = ''
      try {
        this.current = await createCollectBatch(payload)
        this.flash = `批次 ${this.current.batch_no} 已创建，共 ${this.current.counts.total} 条候选`
        await this.loadList()
        return this.current
      } finally {
        this.busy = false
      }
    },
    async run(id: string) {
      this.busy = true
      this.error = ''
      try {
        this.current = await runCollectBatch(id)
        const c = this.current.counts
        this.flash = `批次 ${this.current.status_label}：待处理 ${c.pending} · 已入库 ${c.inserted} · 重复 ${c.duplicate} · 失败 ${c.failed}`
        await Promise.all([this.loadItems(id), this.loadReconciliation(id), this.loadList(), this.loadHealth()])
        return this.current
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '批次运行失败'
        throw error
      } finally {
        this.busy = false
      }
    },
    async toggleOutage(sourceCode: string, online: boolean, reason = '') {
      const result = await setSourceHealth(sourceCode, online, reason)
      this.sourceHealth = result.items
    },
  },
})
