/** 值班墙时钟：每秒推进一次（只在顶部 LIVE 区使用）。 */
import { onBeforeUnmount, ref } from 'vue'

export function useTicker() {
  const now = ref(new Date())
  const timer = setInterval(() => {
    now.value = new Date()
  }, 1000)
  onBeforeUnmount(() => clearInterval(timer))
  return now
}
