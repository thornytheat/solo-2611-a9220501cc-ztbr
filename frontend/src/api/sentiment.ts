import http from './http'
import type { RescoreReport, SentimentSummary } from '../types/domain'

export async function fetchSummary(): Promise<SentimentSummary> {
  const { data } = await http.get<SentimentSummary>('/sentiment/summary')
  return data
}

export async function rescore(): Promise<RescoreReport> {
  const { data } = await http.post<RescoreReport>('/sentiment/rescore')
  return data
}
