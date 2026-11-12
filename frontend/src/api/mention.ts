import http from './http'
import type { MentionDetail, MentionItem, MentionListResponse } from '../types/domain'

export interface MentionQuery {
  group_code?: string
  source_code?: string
  label?: string
  review_status?: string
  q?: string
  days?: number
  sort?: string
  limit?: number
  offset?: number
}

export async function fetchMentions(query: MentionQuery): Promise<MentionListResponse> {
  const { data } = await http.get<MentionListResponse>('/mentions', { params: query })
  return data
}

export async function fetchMention(id: string): Promise<MentionDetail> {
  const { data } = await http.get<MentionDetail>(`/mentions/${id}`)
  return data
}

export async function reviewMention(id: string, finalLabel: string, note: string): Promise<MentionDetail> {
  const { data } = await http.post<MentionDetail>(`/mentions/${id}/review`, {
    final_label: finalLabel,
    note,
  })
  return data
}

export async function fetchReviewQueue(limit = 20): Promise<{ items: MentionItem[]; total: number }> {
  const { data } = await http.get<{ items: MentionItem[]; total: number }>('/mentions/review-queue', {
    params: { limit },
  })
  return data
}
