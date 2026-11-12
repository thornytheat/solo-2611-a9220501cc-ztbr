import http from './http'
import type {
  CollectBatch,
  CollectBatchItem,
  CollectBatchReconciliation,
  SourceHealth,
} from '../types/domain'

export interface CreateBatchPayload {
  brand_key: string
  source_codes: string[]
  window_start: string
  window_end: string
}

export interface BatchItemsQuery {
  source_code?: string
  status?: string
  limit?: number
  offset?: number
}

export async function createCollectBatch(payload: CreateBatchPayload): Promise<CollectBatch> {
  const { data } = await http.post<CollectBatch>('/collect/batches', payload)
  return data
}

export async function runCollectBatch(batchId: string): Promise<CollectBatch> {
  const { data } = await http.post<CollectBatch>(`/collect/batches/${batchId}/run`)
  return data
}

export async function fetchCollectBatches(
  limit = 20,
  offset = 0,
): Promise<{ items: CollectBatch[]; total: number; limit: number; offset: number }> {
  const { data } = await http.get('/collect/batches', { params: { limit, offset } })
  return data
}

export async function fetchCollectBatch(batchId: string): Promise<CollectBatch> {
  const { data } = await http.get<CollectBatch>(`/collect/batches/${batchId}`)
  return data
}

export async function fetchBatchItems(
  batchId: string,
  query: BatchItemsQuery = {},
): Promise<{ items: CollectBatchItem[]; total: number; limit: number; offset: number }> {
  const { data } = await http.get(`/collect/batches/${batchId}/items`, { params: query })
  return data
}

export async function fetchBatchReconciliation(batchId: string): Promise<CollectBatchReconciliation> {
  const { data } = await http.get<CollectBatchReconciliation>(
    `/collect/batches/${batchId}/reconciliation`,
  )
  return data
}

export async function fetchSourceHealth(): Promise<{ items: SourceHealth[] }> {
  const { data } = await http.get('/collect/source-health')
  return data
}

export async function setSourceHealth(
  sourceCode: string,
  online: boolean,
  reason = '',
): Promise<{ items: SourceHealth[] }> {
  const { data } = await http.post(`/collect/source-health/${sourceCode}`, null, {
    params: { online, reason },
  })
  return data
}
