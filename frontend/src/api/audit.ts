import http from './http'
import type { AuditEntry } from '../types/domain'

export async function fetchAudit(limit = 40, action?: string): Promise<{ items: AuditEntry[] }> {
  const { data } = await http.get<{ items: AuditEntry[] }>('/audit', { params: { limit, action } })
  return data
}
