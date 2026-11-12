/** 通用异步状态：loading / error / data，错误态可重试。 */
import { ref, type Ref } from 'vue'
import type { ApiError } from '../types/api'

export interface AsyncState<T> {
  data: Ref<T | null>
  loading: Ref<boolean>
  error: Ref<ApiError | null>
  run: () => Promise<T | null>
}

export function useAsync<T>(loader: () => Promise<T>, options: { immediate?: boolean } = {}): AsyncState<T> {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const error = ref<ApiError | null>(null)

  async function run(): Promise<T | null> {
    loading.value = true
    error.value = null
    try {
      const result = await loader()
      data.value = result
      return result
    } catch (err) {
      error.value = err as ApiError
      return null
    } finally {
      loading.value = false
    }
  }

  if (options.immediate !== false) {
    void run()
  }
  return { data, loading, error, run }
}
