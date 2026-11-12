/** 输入防抖：筛选框每次敲字不必都打接口。 */
import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

export function useDebounced<T>(source: Ref<T>, delay = 320): Ref<T> {
  const debounced = ref(source.value) as Ref<T>
  let timer: ReturnType<typeof setTimeout> | null = null

  watch(source, (value) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      debounced.value = value
      timer = null
    }, delay)
  })

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer)
  })

  return debounced
}
