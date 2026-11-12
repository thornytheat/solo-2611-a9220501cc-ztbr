/** 情感证据词高亮：按后端返回的 offset/length 切分正文（offset 对应归一化后的正文）。 */
import type { Hit } from '../types/domain'

export interface Segment {
  text: string
  hit: Hit | null
}

export function splitByHits(text: string, hits: Hit[]): Segment[] {
  if (!text) return []
  if (!hits.length) return [{ text, hit: null }]
  const sorted = [...hits].sort((a, b) => a.offset - b.offset)
  const segments: Segment[] = []
  let cursor = 0
  for (const hit of sorted) {
    if (hit.offset < cursor) continue
    if (hit.offset > cursor) {
      segments.push({ text: text.slice(cursor, hit.offset), hit: null })
    }
    segments.push({ text: text.slice(hit.offset, hit.offset + hit.length), hit })
    cursor = hit.offset + hit.length
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), hit: null })
  }
  return segments
}

export function hitRole(hit: Hit): string {
  if (hit.negated) return 'negated'
  if (hit.polarity > 0) return 'positive'
  return 'negative'
}
