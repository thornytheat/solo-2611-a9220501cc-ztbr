import http from './http'
import type { GroupItem, TrialResult } from '../types/domain'

export interface GroupListResponse {
  items: GroupItem[]
  totals: { groups: number; enabled: number; mentions: number; neg: number }
  anchor_at: string | null
}

export async function fetchGroups(): Promise<GroupListResponse> {
  const { data } = await http.get<GroupListResponse>('/groups')
  return data
}

export interface GroupUpdatePayload {
  name?: string
  keywords?: string[]
  synonyms?: string[]
  excludes?: string[]
  enabled?: boolean
  priority?: number
  z_threshold?: number
  min_count?: number
  owner_note?: string
}

export async function updateGroup(id: string, payload: GroupUpdatePayload): Promise<GroupItem> {
  const { data } = await http.patch<GroupItem>(`/groups/${id}`, payload)
  return data
}

export interface GroupCreatePayload extends GroupUpdatePayload {
  code: string
  name: string
  brand_key: string
  keywords: string[]
}

export async function createGroup(payload: GroupCreatePayload): Promise<GroupItem> {
  const { data } = await http.post<GroupItem>('/groups', payload)
  return data
}

export interface TrialPayload {
  code?: string
  keywords: string[]
  synonyms: string[]
  excludes: string[]
  source_code?: string | null
}

export async function trialRecall(payload: TrialPayload): Promise<TrialResult> {
  const { data } = await http.post<TrialResult>('/groups/trial', payload)
  return data
}
