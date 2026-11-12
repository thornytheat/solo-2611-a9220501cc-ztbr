import http from './http'
import type { CollectReport } from '../types/domain'

export async function runCollection(): Promise<CollectReport> {
  const { data } = await http.post<CollectReport>('/collect/run')
  return data
}

export interface CollectRun {
  id: string
  created_at: string
  actor_email: string
  detail: Record<string, number>
}

export async function fetchRuns(limit = 8): Promise<{ items: CollectRun[] }> {
  const { data } = await http.get<{ items: CollectRun[] }>('/collect/runs', { params: { limit } })
  return data
}
