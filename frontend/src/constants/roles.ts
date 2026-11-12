/** 角色与权限（镜像 backend/src/constants/roles.py）。 */
import type { UserRole } from '../types/user'

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: '舆情总监',
  analyst: '值班分析师',
  client: '品牌方',
}

export const ROLE_SCOPE: Record<UserRole, string> = {
  admin: '关键词组与词典 · 阈值 · 发布日报',
  analyst: '采集 · 情感复核 · 预警认领处置',
  client: '只读自己品牌（不含内部备注与处置记录）',
}

export const PERMISSION_LABELS: Record<string, string> = {
  'mentions:read': '读取提及',
  'mentions:review': '情感复核',
  'groups:read': '读取关键词组',
  'groups:write': '编辑关键词组',
  'groups:trial': '召回试算',
  'collect:run': '运行采集',
  'sentiment:rescore': '重算情感',
  'bursts:read': '读取预警',
  'bursts:detect': '运行爆发检测',
  'bursts:claim': '认领事件',
  'bursts:dispose': '处置事件',
  'export:daily': '导出日报',
  'audit:read': '读取审计日志',
}
