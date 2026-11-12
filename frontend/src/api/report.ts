import http from './http'
import type { DailyReport } from '../types/domain'

export async function previewDaily(): Promise<DailyReport> {
  const { data } = await http.get<DailyReport>('/export/preview')
  return data
}

export async function exportDaily(): Promise<DailyReport> {
  const { data } = await http.get<DailyReport>('/export/daily')
  return data
}
