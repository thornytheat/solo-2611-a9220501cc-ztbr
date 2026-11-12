"""日报导出：评估日 Top5 负面 + 证据词 + 爆发事件 → Markdown（可下载、落盘 artifacts）。"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.brands import BRAND_CATALOG
from src.constants.enums import BRAND_LABELS, SENTIMENT_LABELS, SOURCE_LABELS
from src.constants.limits import EXPORT_TOP_NEGATIVE
from src.constants.log_templates import ACTION_EXPORT_DAILY
from src.models.burst_alert import BurstAlert
from src.models.keyword_group import KeywordGroup
from src.models.mention import Mention
from src.models.sentiment_score import SentimentScore
from src.models.user import User
from src.services import audit_service
from src.services.analysis.burst_detector import DETECTION_VERSION
from src.services.analysis.sentiment_analyzer import ALGORITHM_VERSION
from src.services.sentiment_service import top_evidence_words
from src.utils.errors import AppError
from src.utils.timeutil import to_local

ARTIFACT_DIR = os.environ.get("ARTIFACT_DIR", "artifacts")


def _day_bounds(anchor: datetime) -> tuple[datetime, datetime]:
    local = to_local(anchor)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def build_daily_report(db: Session, brand_scope: str | None) -> dict:
    anchor = db.execute(select(func.max(Mention.published_at))).scalar_one_or_none()
    if anchor is None:
        raise AppError(codes.EXPORT_EMPTY, "还没有任何提及，无法导出日报", "mention table empty")
    start, end = _day_bounds(anchor)

    neg_stmt = (
        select(Mention, SentimentScore, KeywordGroup)
        .join(SentimentScore, SentimentScore.mention_id == Mention.id)
        .join(KeywordGroup, KeywordGroup.id == Mention.group_id)
        .where(
            Mention.published_at >= start,
            Mention.published_at < end,
            SentimentScore.final_label == "neg",
        )
        .order_by(SentimentScore.score.asc(), Mention.engagement.desc())
        .limit(EXPORT_TOP_NEGATIVE)
    )
    if brand_scope:
        neg_stmt = neg_stmt.where(Mention.brand_key == brand_scope)
    top_negative = db.execute(neg_stmt).all()
    if not top_negative:
        raise AppError(codes.EXPORT_EMPTY, "当日没有可导出的负面提及", f"day={start.date()}")

    dist_stmt = (
        select(SentimentScore.final_label, func.count())
        .join(Mention, Mention.id == SentimentScore.mention_id)
        .where(Mention.published_at >= start, Mention.published_at < end)
        .group_by(SentimentScore.final_label)
    )
    if brand_scope:
        dist_stmt = dist_stmt.where(Mention.brand_key == brand_scope)
    distribution = {label: int(count) for label, count in db.execute(dist_stmt).all()}
    total = sum(distribution.values())

    alert_stmt = (
        select(BurstAlert, KeywordGroup)
        .join(KeywordGroup, KeywordGroup.id == BurstAlert.group_id)
        .where(BurstAlert.window_start >= start, BurstAlert.window_start < end)
        .order_by(BurstAlert.z_score.desc())
    )
    if brand_scope:
        alert_stmt = alert_stmt.where(BurstAlert.brand_key == brand_scope)
    alerts = db.execute(alert_stmt).all()

    group_stmt = (
        select(KeywordGroup, SentimentScore.final_label, func.count())
        .join(Mention, Mention.group_id == KeywordGroup.id)
        .join(SentimentScore, SentimentScore.mention_id == Mention.id)
        .where(Mention.published_at >= start, Mention.published_at < end)
        .group_by(KeywordGroup.id, SentimentScore.final_label)
    )
    if brand_scope:
        group_stmt = group_stmt.where(KeywordGroup.brand_key == brand_scope)
    per_group: dict[str, dict] = {}
    for group, label, count in db.execute(group_stmt).all():
        entry = per_group.setdefault(group.code, {"name": group.name, "brand": group.brand_key, "pos": 0, "neu": 0, "neg": 0})
        entry[label] += int(count)

    evidence = top_evidence_words(db, brand_scope, limit=8)
    generated_at = datetime.now()
    lines: list[str] = []
    lines.append(f"# {settings.brand} 舆情日报 · {start.date().isoformat()}")
    lines.append("")
    lines.append(f"> 委托方：{settings.org_name}　|　报告生成：{generated_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 口径：情感算法 `{ALGORITHM_VERSION}`（词典 + 否定/程度规则）　爆发算法 `{DETECTION_VERSION}`（7 天同小时基线 z）")
    lines.append("")
    lines.append("## 一、当日概况")
    lines.append("")
    lines.append(f"- 当日提及：**{total}** 条（机器打分后再人工复核）")
    lines.append(
        f"- 情感分布：正面 {distribution.get('pos', 0)} / 中性 {distribution.get('neu', 0)} / 负面 {distribution.get('neg', 0)}"
        f"（负面率 {round(distribution.get('neg', 0) / total * 100, 1) if total else 0}%）"
    )
    lines.append(f"- 爆发事件：**{len(alerts)}** 个（critical {sum(1 for a, _ in alerts if a.level == 'critical')}）")
    if brand_scope:
        lines.append(f"- 数据域：{BRAND_LABELS.get(brand_scope, brand_scope)}（品牌方只读视图）")
    lines.append("")
    lines.append("## 二、Top5 负面提及与证据词")
    lines.append("")
    for index, (mention, score, group) in enumerate(top_negative, start=1):
        words = [hit["word"] for hit in (score.hits or []) if hit.get("polarity", 0) < 0][:5]
        negated = [hit["word"] for hit in (score.hits or []) if hit.get("negated")][:3]
        lines.append(f"### {index}. {mention.title}")
        lines.append("")
        lines.append(f"- 组别：{group.name}（{BRAND_LABELS.get(mention.brand_key, mention.brand_key)}）")
        lines.append(f"- 来源：{SOURCE_LABELS.get(mention.source_code, mention.source_code)}　作者：{mention.author}")
        page_time = to_local(mention.published_at)
        lines.append(f"- 发布时间：{page_time.strftime('%Y-%m-%d %H:%M')}　情感分：**{score.score:.4f}**（{SENTIMENT_LABELS[score.final_label]}）")
        lines.append(f"- 证据词：{'、'.join(words) if words else '（无负向词典命中）'}" + (f"；否定命中：{'、'.join(negated)}" if negated else ""))
        lines.append(f"- 原文摘录：{mention.body}")
        lines.append("")
    lines.append("## 三、分组负面率")
    lines.append("")
    lines.append("| 组别 | 品牌 | 提及 | 负面 | 负面率 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for entry in sorted(per_group.values(), key=lambda item: -(item["neg"] / max(sum(item[k] for k in ('pos', 'neu', 'neg')), 1))):
        group_total = entry["pos"] + entry["neu"] + entry["neg"]
        lines.append(
            f"| {entry['name']} | {BRAND_LABELS.get(entry['brand'], entry['brand'])} | {group_total} | {entry['neg']} "
            f"| {round(entry['neg'] / group_total * 100, 1) if group_total else 0}% |"
        )
    lines.append("")
    lines.append("## 四、爆发事件")
    lines.append("")
    if alerts:
        lines.append("| 组别 | 窗口 | 量 | 基线 μ | σ | z | 等级 | 处置 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for alert, group in alerts:
            window = to_local(alert.window_start).strftime("%H:%M")
            lines.append(
                f"| {group.name} | {window} | {alert.count} | {alert.baseline_mean:.2f} | {alert.baseline_std:.2f} "
                f"| {alert.z_score:.2f} | {alert.level} | {alert.status} |"
            )
    else:
        lines.append("当日无爆发事件（z 阈值内）。")
    lines.append("")
    lines.append("## 五、高频负面证据词")
    lines.append("")
    if evidence:
        lines.append(" / ".join(f"`{item['word']}`×{item['count']}" for item in evidence))
    else:
        lines.append("（当日无负面证据词）")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*本报告由 {settings.brand} 自动生成：采集 → 情感打分 → 爆发检测 → 人工复核 → 日报导出。*")
    markdown = "\n".join(lines) + "\n"

    filename = f"{settings.brand}-daily-{start.date().isoformat()}.md"
    try:
        os.makedirs(ARTIFACT_DIR, exist_ok=True)
        with open(os.path.join(ARTIFACT_DIR, filename), "w", encoding="utf-8") as handle:
            handle.write(markdown)
    except OSError:
        pass

    return {
        "filename": filename,
        "eval_day": start.date().isoformat(),
        "markdown": markdown,
        "stats": {
            "total": total,
            "distribution": distribution,
            "neg_rate": round(distribution.get("neg", 0) / total, 4) if total else 0.0,
            "top_negative": len(top_negative),
            "alerts": len(alerts),
            "evidence_words": evidence,
        },
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "brands": len(BRAND_CATALOG),
    }


def export_daily(db: Session, user: User, brand_scope: str | None, trace_id: str = "") -> dict:
    report = build_daily_report(db, brand_scope)
    audit_service.record(
        db,
        action=ACTION_EXPORT_DAILY,
        actor=user,
        entity_type="export",
        entity_id=report["filename"],
        detail={key: report["stats"][key] for key in ("total", "alerts", "neg_rate")},
        trace_id=trace_id,
    )
    db.commit()
    return report
