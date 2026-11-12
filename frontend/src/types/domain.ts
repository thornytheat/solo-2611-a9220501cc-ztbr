/** 领域类型：与后端 service.serialize* 的字段逐字对应。 */

export type SentimentLabel = 'pos' | 'neu' | 'neg'
export type BurstLevel = 'watch' | 'alert' | 'critical'
export type BurstStatus = 'open' | 'claimed' | 'handled' | 'dismissed'
export type ReviewStatus = 'auto' | 'pending' | 'confirmed' | 'corrected'
export type SourceCode = 'news_wire' | 'microblog' | 'vertical_forum' | 'video_agg'
export type BrandKey = 'coffee' | 'maternal' | 'outdoor' | 'pet' | 'homecare' | 'snack'

export interface EnumOption<T extends string = string> {
  value: T
  label: string
}

export interface SourceMeta {
  code: SourceCode
  name: string
  channel: string
  base_url: string
  latency_hint: string
  auth: string
  daily_quota: number
}

export interface BrandMeta {
  key: BrandKey
  name: string
  short?: string
  category: string
  since: string
  scene: string
  client_email?: string
}

export interface GroupStats {
  mentions: number
  recent_24h: number
  neg: number
  pos: number
  neu: number
  neg_rate: number
  last_mention_at: string | null
}

export interface GroupItem {
  id: string
  code: string
  name: string
  brand_key: BrandKey
  brand_label: string
  brand_category?: string
  keywords: string[]
  synonyms: string[]
  excludes: string[]
  enabled: boolean
  priority: number
  z_threshold: number
  min_count: number
  owner_note: string
  stats?: GroupStats
}

export interface Hit {
  word: string
  offset: number
  length: number
  polarity: number
  weight: number
  degree: string | null
  degree_ratio: number
  negated: boolean
  negator: string | null
  contribution: number
}

export interface SentimentInfo {
  score: number
  label: SentimentLabel
  final_label: SentimentLabel
  label_text: string
  confidence: number
  review_status: ReviewStatus
  review_status_text: string
  positive_count: number
  negative_count: number
  negation_count: number
  degree_count: number
  rhetoric_count: number
  exclaim_count: number
  reviewer_email: string
  review_note: string
  reviewed_at: string | null
  algorithm_version: string
  hits: Hit[]
}

export interface MentionItem {
  id: string
  external_id: string
  group_id: string
  group_code: string
  group_name: string
  brand_key: BrandKey
  brand_label: string
  source_code: SourceCode
  source_label: string
  title: string
  excerpt: string
  author: string
  author_followers: number
  url: string
  engagement: number
  published_at: string
  sentiment: SentimentInfo
}

export interface FacetBucket {
  value: string
  label: string
  count: number
}

export interface BandPoint {
  hour: number
  pos: number
  neu: number
  neg: number
}

export interface MentionListResponse {
  items: MentionItem[]
  total: number
  limit: number
  offset: number
  anchor_at: string | null
  facets: {
    label: FacetBucket[]
    source: FacetBucket[]
    review: FacetBucket[]
    group: Record<string, number>
    total: number
    neg_rate: number
  }
  band: BandPoint[]
}

export interface RelatedMention {
  id: string
  title: string
  published_at: string
  label: SentimentLabel
  source_code: SourceCode
  score: number
}

export interface MentionAlertRef {
  id: string
  level: BurstLevel
  z_score: number
  count: number
  window_start: string
  status: BurstStatus
}

export interface MentionDetail extends MentionItem {
  body: string
  content_hash: string
  fetched_at: string
  related: RelatedMention[]
  alerts: MentionAlertRef[]
  audit: AuditEntry[]
  group: {
    code: string
    name: string
    keywords: string[]
    synonyms: string[]
    excludes: string[]
    z_threshold: number
    min_count: number
  }
}

export interface BurstItem {
  id: string
  group_id: string
  group_code: string
  group_name: string
  brand_key: BrandKey
  brand_label: string
  window_start: string
  window_end: string
  eval_day: string
  count: number
  baseline_mean: number
  baseline_std: number
  z_score: number
  level: BurstLevel
  level_label: string
  status: BurstStatus
  status_label: string
  merged_windows: string[]
  baseline_series: number[]
  sample_titles: string[]
  claimed_by_email: string
  claimed_at: string | null
  disposition_note: string
  disposed_at: string | null
  detection_version: string
  thresholds: { z: number; min_count: number }
}

export interface BurstListResponse {
  items: BurstItem[]
  levels: FacetBucket[]
  statuses: FacetBucket[]
  total: number
  thresholds: { z_threshold: number; min_count: number; baseline_days: number; sigma_floor: number }
}

export interface TrendPoint {
  hour: number
  count: number
  baseline: number
}

export interface BurstDetail extends BurstItem {
  trend: TrendPoint[]
  audit: AuditEntry[]
  window_mentions: {
    id: string
    title: string
    published_at: string
    label: SentimentLabel
    score: number
    source_code: SourceCode
  }[]
}

export interface BurstDashboard {
  levels: FacetBucket[]
  statuses: FacetBucket[]
  total: number
  top_event: BurstItem | null
  level_counts: Record<BurstLevel, number>
  top_groups: { name: string; count: number }[]
  thresholds: { z_threshold: number; min_count: number; baseline_days: number; sigma_floor: number }
  eval_day: string | null
}

export interface DetectionResult {
  eval_day: string | null
  scanned_hours: number
  events: BurstItem[]
  created: number
  updated: number
  unknown_windows: { group_id: string; window_start: string; count: number; baseline_days: number; z_score: number }[]
  algorithm_version: string
  thresholds: Record<string, number>
  elapsed_ms: number
}

export interface CollectReport {
  scanned: number
  inserted: number
  duplicates: number
  duplicate_reasons: Record<string, number>
  distribution: Record<SentimentLabel, number>
  per_source: { code: SourceCode; label: string; count: number }[]
  per_group: Record<string, number>
  skipped_groups: string[]
  total_mentions: number
  elapsed_ms: number
  window_note: string
  finished_at: string
}

export interface SentimentGroupRow {
  id: string
  code: string
  name: string
  brand_key: BrandKey
  brand_label: string
  mentions: number
  pos: number
  neu: number
  neg: number
  neg_rate: number
}

export interface SentimentSummary {
  distribution: { value: SentimentLabel; label: string; count: number; ratio: number }[]
  total: number
  neg_rate: number
  avg_neg_rate: number
  review: FacetBucket[]
  groups: SentimentGroupRow[]
  algorithm_version: string
  scope: string | null
  evidence_words: { word: string; count: number }[]
}

export interface RescoreReport {
  scored: number
  changed: number
  review_preserved: number
  distribution: Record<string, number>
  neg_rate: number
  algorithm_version: string
  elapsed_ms: number
  scored_at: string
}

export interface TrialSample {
  external_id: string
  title: string
  source_code: SourceCode
  brand_key: BrandKey
  published_at: string
  hit_keywords: string[]
  hit_synonyms: string[]
  hit_excludes: string[]
}

export interface TrialResult {
  scanned: number
  matched: number
  kept: number
  excluded: number
  recall_rate: number
  precision_hint: number
  per_source: Record<string, number>
  samples: TrialSample[]
  corpus_note: string
}

export interface DailyReport {
  filename: string
  eval_day: string
  markdown: string
  stats: {
    total: number
    distribution: Record<string, number>
    neg_rate: number
    top_negative: number
    alerts: number
    evidence_words: { word: string; count: number }[]
  }
  generated_at: string
  brands: number
}

export interface AuditEntry {
  id: string
  action: string
  actor_email: string
  entity_type: string
  entity_id: string
  detail: Record<string, unknown>
  trace_id: string
  created_at: string
}

export interface BootstrapPayload {
  brand: string
  org: { name: string; size: string; brands_served: number; sources: number }
  enums: {
    sentiment: EnumOption<SentimentLabel>[]
    burst_level: EnumOption<BurstLevel>[]
    burst_status: EnumOption<BurstStatus>[]
    review_status: EnumOption<ReviewStatus>[]
    source: EnumOption<SourceCode>[]
    brand: EnumOption<BrandKey>[]
    role: EnumOption[]
    audit_action: EnumOption[]
  }
  sources: SourceMeta[]
  brands: BrandMeta[]
  groups: GroupItem[]
  thresholds: Record<string, number>
  algorithms: {
    sentiment: { version: string; lexicon: Record<string, number> }
    burst: { version: string }
  }
  permissions: Record<string, string[]>
  counts: { mentions: number; bursts: number; groups: number }
  scope: string | null
}

export interface DictionaryPayload {
  positive: { word: string; weight: number }[]
  negative: { word: string; weight: number }[]
  degree: { word: string; weight: number }[]
  negators: string[]
  rhetorical: string[]
  sizes: Record<string, number>
}
