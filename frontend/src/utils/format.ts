/** 展示格式化：时间一律按上海时区（后端已给 +08:00 的 ISO 串）。 */
const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

export function pad(value: number): string {
  return value.toString().padStart(2, '0')
}

export function parseTime(value: string | null | undefined): Date | null {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function timeHM(value: string | null | undefined): string {
  const date = parseTime(value)
  if (!date) return '--:--'
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function dateTime(value: string | null | undefined): string {
  const date = parseTime(value)
  if (!date) return '—'
  return `${date.getMonth() + 1}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function dayLabel(value: string | null | undefined): string {
  const date = parseTime(value)
  if (!date) return '—'
  return `${date.getMonth() + 1}月${date.getDate()}日 周${WEEKDAYS[date.getDay()]}`
}

export function clockLabel(value: string | null | undefined): string {
  const date = parseTime(value)
  if (!date) return '--:--:--'
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

export function relativeHours(value: string | null | undefined, anchor: string | null | undefined): string {
  const a = parseTime(value)
  const b = parseTime(anchor ?? null)
  if (!a || !b) return ''
  const diff = Math.max(0, Math.round((b.getTime() - a.getTime()) / 3600000))
  if (diff < 1) return '1 小时内'
  if (diff < 24) return `${diff} 小时前`
  return `${Math.round(diff / 24)} 天前`
}

export function pct(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`
}

export function fixed(value: number, digits = 2): string {
  return value.toFixed(digits)
}

export function signed(value: number, digits = 3): string {
  return `${value > 0 ? '+' : ''}${value.toFixed(digits)}`
}

export function compactNumber(value: number): string {
  if (value >= 10000) return `${(value / 10000).toFixed(1)}w`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
  return `${value}`
}

export function levelOfScore(score: number): 'neg' | 'neu' | 'pos' {
  if (score <= -0.2) return 'neg'
  if (score >= 0.2) return 'pos'
  return 'neu'
}
