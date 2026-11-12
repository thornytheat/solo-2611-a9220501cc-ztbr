export interface ApiError {
  code: string
  message: string
  detail?: string
  traceId?: string | null
  status?: number
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}
