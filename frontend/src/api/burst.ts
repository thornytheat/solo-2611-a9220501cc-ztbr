import http from './http'
import type { BurstDashboard, BurstDetail, BurstItem, BurstListResponse, DetectionResult } from '../types/domain'

export async function fetchBursts(params: { level?: string; status?: string; limit?: number } = {}): Promise<BurstListResponse> {
  const { data } = await http.get<BurstListResponse>('/bursts', { params })
  return data
}

export async function fetchBurstDashboard(): Promise<BurstDashboard> {
  const { data } = await http.get<BurstDashboard>('/bursts/dashboard')
  return data
}

export async function fetchBurst(id: string): Promise<BurstDetail> {
  const { data } = await http.get<BurstDetail>(`/bursts/${id}`)
  return data
}

export async function detectBursts(): Promise<DetectionResult> {
  const { data } = await http.post<DetectionResult>('/bursts/detect')
  return data
}

export async function claimBurst(id: string): Promise<BurstItem> {
  const { data } = await http.post<BurstItem>(`/bursts/${id}/claim`)
  return data
}

export async function disposeBurst(id: string, status: string, note: string): Promise<BurstItem> {
  const { data } = await http.post<BurstItem>(`/bursts/${id}/dispose`, { status, note })
  return data
}
