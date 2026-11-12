/** 共享枚举（前端镜像，后端 src/constants/enums.py 为唯一事实源）。 */
import type { BurstLevel, BurstStatus, ReviewStatus, SentimentLabel } from '../types/domain'

export const SENTIMENT_LABELS: Record<SentimentLabel, string> = {
  pos: '正面',
  neu: '中性',
  neg: '负面',
}

export const BURST_LEVEL_LABELS: Record<BurstLevel, string> = {
  watch: '关注',
  alert: '预警',
  critical: '危急',
}

export const BURST_STATUS_LABELS: Record<BurstStatus, string> = {
  open: '待认领',
  claimed: '已认领',
  handled: '已处置',
  dismissed: '已排除',
}

export const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  auto: '机器判定',
  pending: '待复核',
  confirmed: '复核确认',
  corrected: '人工修正',
}

export const SENTIMENT_ORDER: SentimentLabel[] = ['neg', 'neu', 'pos']
export const BURST_LEVEL_ORDER: BurstLevel[] = ['critical', 'alert', 'watch']
