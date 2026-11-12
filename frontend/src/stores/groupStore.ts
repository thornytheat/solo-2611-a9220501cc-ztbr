import { defineStore } from 'pinia'
import { createGroup, fetchGroups, trialRecall, updateGroup, type GroupCreatePayload, type GroupUpdatePayload, type TrialPayload } from '../api/group'
import type { GroupItem, TrialResult } from '../types/domain'

interface GroupState {
  items: GroupItem[]
  totals: { groups: number; enabled: number; mentions: number; neg: number }
  selectedId: string
  trial: TrialResult | null
  loading: boolean
  saving: boolean
  error: string
  flash: string
}

export const useGroupStore = defineStore('group', {
  state: (): GroupState => ({
    items: [],
    totals: { groups: 0, enabled: 0, mentions: 0, neg: 0 },
    selectedId: '',
    trial: null,
    loading: false,
    saving: false,
    error: '',
    flash: '',
  }),
  getters: {
    selected: (state): GroupItem | null => state.items.find((item) => item.id === state.selectedId) ?? null,
    enabledCount: (state): number => state.items.filter((item) => item.enabled).length,
  },
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchGroups()
        this.items = result.items
        this.totals = result.totals
        if (!this.selectedId || !this.items.some((item) => item.id === this.selectedId)) {
          this.selectedId = this.items[0]?.id ?? ''
        }
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '关键词组加载失败'
      } finally {
        this.loading = false
      }
    },
    select(id: string) {
      this.selectedId = id
      this.trial = null
      this.flash = ''
    },
    async save(payload: GroupUpdatePayload) {
      if (!this.selectedId) return null
      this.saving = true
      this.error = ''
      try {
        const updated = await updateGroup(this.selectedId, payload)
        this.items = this.items.map((item) => (item.id === updated.id ? { ...item, ...updated } : item))
        this.flash = `已保存 ${updated.name}`
        return updated
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '保存失败'
        return null
      } finally {
        this.saving = false
      }
    },
    async create(payload: GroupCreatePayload) {
      this.saving = true
      this.error = ''
      try {
        const created = await createGroup(payload)
        await this.load()
        this.selectedId = created.id
        this.flash = `已新建 ${created.name}`
        return created
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '新建失败'
        return null
      } finally {
        this.saving = false
      }
    },
    async trialRun(payload: TrialPayload) {
      this.error = ''
      try {
        this.trial = await trialRecall(payload)
        return this.trial
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '试算失败'
        return null
      }
    },
  },
})
