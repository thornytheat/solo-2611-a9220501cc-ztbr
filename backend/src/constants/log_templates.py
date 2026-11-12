"""审计动作名（前后端共用同一批字符串，出现在 audit 表与前端时间线）。"""
from __future__ import annotations

ACTION_LOGIN = "auth.login"
ACTION_LOGIN_FAILED = "auth.login_failed"
ACTION_COLLECT_RUN = "collect.run"
ACTION_COLLECT_BATCH_CREATE = "collect.batch_create"
ACTION_COLLECT_BATCH_RUN = "collect.batch_run"
ACTION_SENTIMENT_RESCORE = "sentiment.rescore"
ACTION_SENTIMENT_REVIEW = "sentiment.review"
ACTION_BURST_DETECT = "burst.detect"
ACTION_BURST_CLAIM = "burst.claim"
ACTION_BURST_DISPOSE = "burst.dispose"
ACTION_GROUP_CREATE = "group.create"
ACTION_GROUP_UPDATE = "group.update"
ACTION_GROUP_TRIAL = "group.trial"
ACTION_EXPORT_DAILY = "export.daily"

ACTION_LABELS: dict[str, str] = {
    ACTION_LOGIN: "登录",
    ACTION_LOGIN_FAILED: "登录失败",
    ACTION_COLLECT_RUN: "运行采集",
    ACTION_COLLECT_BATCH_CREATE: "创建补采批次",
    ACTION_COLLECT_BATCH_RUN: "运行补采批次",
    ACTION_SENTIMENT_RESCORE: "重算情感",
    ACTION_SENTIMENT_REVIEW: "情感复核",
    ACTION_BURST_DETECT: "爆发检测",
    ACTION_BURST_CLAIM: "认领事件",
    ACTION_BURST_DISPOSE: "处置事件",
    ACTION_GROUP_CREATE: "新建关键词组",
    ACTION_GROUP_UPDATE: "更新关键词组",
    ACTION_GROUP_TRIAL: "召回试算",
    ACTION_EXPORT_DAILY: "导出日报",
}
