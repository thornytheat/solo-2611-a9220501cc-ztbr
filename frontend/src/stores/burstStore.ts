import { defineStore } from 'pinia'
import {
  claimBurst,
  detectBursts,
  disposeBurst,
  fetchBurst,
  fetchBurstDashboard,
  fetchBursts,
} from '../api/burst'
import type { BurstDashboard, BurstDetail, BurstItem, BurstListResponse, DetectionResult } from '../types/domain'

interface BurstState {
  list: BurstListResponse | null
  dashboard: BurstDashboard | null
  detail: BurstDetail | null
  selectedId: string
  detection: DetectionResult | null
  level: string
  status: string
  loading: boolean
  busy: boolean
  error: string
  flash: string
}

export const useBurstStore = defineStore('burst', {
  state: (): BurstState => ({
    list: null,
    dashboard: null,
    detail: null,
    selectedId: '',
    detection: null,
    level: '',
    status: '',
    loading: false,
    busy: false,
    error: '',
    flash: '',
  }),
  getters: {
    items: (state): BurstItem[] => state.list?.items ?? [],
    selected: (state): BurstItem | null =>
      state.detail ?? state.list?.items.find((item) => item.id === state.selectedId) ?? null,
    levels: (state) => state.list?.levels ?? [],
    statuses: (state) => state.list?.statuses ?? [],
  },
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const params: { level?: string; status?: string; limit?: number } = { limit: 40 }
        if (this.level) params.level = this.level
        if (this.status) params.status = this.status
        const [list, dashboard] = await Promise.all([fetchBursts(params), fetchBurstDashboard()])
        this.list = list
        this.dashboard = dashboard
        if (!this.selectedId && list.items.length) {
          this.selectedId = list.items[0].id
          await this.loadDetail(list.items[0].id)
        }
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '预警加载失败'
      } finally {
        this.loading = false
      }
    },
    async loadDetail(id: string) {
      this.selectedId = id
      try {
        this.detail = await fetchBurst(id)
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '事件详情加载失败'
      }
    },
    async detect() {
      this.busy = true
      this.error = ''
      try {
        this.detection = await detectBursts()
        this.flash = `检测完成：${this.detection.events.length} 个事件（新建 ${this.detection.created} / 更新 ${this.detection.updated}，${this.detection.elapsed_ms}ms）`
        await this.load()
        if (this.detection.events.length) {
          await this.loadDetail(this.detection.events[0].id)
        }
        return this.detection
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '检测失败'
        return null
      } finally {
        this.busy = false
      }
    },
    async claim(id: string) {
      this.busy = true
      try {
        const updated = await claimBurst(id)
        this.flash = `已认领：${updated.group_name} ${updated.window_start.slice(11, 16)}`
        await this.load()
        await this.loadDetail(id)
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '认领失败'
      } finally {
        this.busy = false
      }
    },
    async dispose(id: string, status: string, note: string) {
      this.busy = true
      try {
        const updated = await disposeBurst(id, status, note)
        this.flash = `已处置：${updated.group_name} → ${updated.status_label}`
        await this.load()
        await this.loadDetail(id)
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '处置失败'
      } finally {
        this.busy = false
      }
    },
  },
})
