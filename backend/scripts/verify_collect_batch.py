"""补采批次端到端验证（真实 Postgres，不经过 HTTP）。

覆盖：
1. 创建批次 → 逐源处理 → 全部成功 → 计数封闭且与入库明细对账一致；
2. 中断注入 → 批次 partial、失败来源台账留痕、已成功来源结果保留；
3. 恢复来源后续跑 → 只处理失败来源 → 批次 completed；
4. 重复运行已完成批次 → 不新增提及（幂等）；
5. 新提及均有 SentimentScore；爆发统计被触发；
6. 再建一个同窗口批次 → 全部候选判为重复，零新增。
"""
from __future__ import annotations

import sys
from datetime import datetime

from sqlalchemy import func, select

from src.config.database import session_scope
from src.models.collect_batch import (
    BATCH_COMPLETED,
    BATCH_PARTIAL,
    ITEM_DUPLICATE,
    ITEM_INSERTED,
    SOURCE_FAILED,
    SOURCE_SUCCESS,
)
from src.models.mention import Mention
from src.models.sentiment_score import SentimentScore
from src.models.user import User
from src.services import collect_batch_service as svc
from src.services.analysis.source_gateway import gateway
from src.utils.timeutil import TZ_SHANGHAI

WS = datetime(2026, 11, 5, 0, 0, tzinfo=TZ_SHANGHAI)
WE = datetime(2026, 11, 13, 0, 0, tzinfo=TZ_SHANGHAI)
SOURCES = ("news_wire", "microblog")

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name} {detail}")
    if not cond:
        failures.append(name)


def main() -> int:
    # 确保所有来源在线
    for code in ("news_wire", "microblog", "vertical_forum", "video_agg"):
        gateway.clear_outage(code)

    with session_scope() as db:
        admin = db.execute(select(User).where(User.role == "admin")).scalar_one()
        mentions_before = int(db.execute(select(func.count(Mention.id))).scalar_one())
        print(f"baseline mentions={mentions_before}")

        # ---- 场景 1：中断一个来源后创建并运行批次 ----
        gateway.set_outage("microblog", "e2e simulated outage")
        created = svc.create_batch(
            db, admin,
            brand_key="coffee",
            source_codes=SOURCES,
            window_start=WS,
            window_end=WE,
            trace_id="e2e-1",
        )
        batch_id = created["id"]
        check("批次初始为 pending", created["status"] == "pending", created["status"])
        check("候选 16 条", created["counts"]["total"] == 16, str(created["counts"]))
        check("初始待处理 16", created["counts"]["pending"] == 16)

        run1 = svc.run_batch(db, admin, batch_id, trace_id="e2e-1")
        check("中断后批次 partial", run1["status"] == BATCH_PARTIAL, run1["status"])
        src_map = {s["source_code"]: s for s in run1["sources"]}
        check("新闻站成功", src_map["news_wire"]["status"] == SOURCE_SUCCESS)
        check("微博来源失败", src_map["microblog"]["status"] == SOURCE_FAILED,
              src_map["microblog"]["error_message"])
        check("失败源 8 条全部留痕 failed",
              src_map["microblog"]["counts"]["failed"] == 8,
              str(src_map["microblog"]["counts"]))
        news_inserted = src_map["news_wire"]["counts"]["inserted"]
        news_dup = src_map["news_wire"]["counts"]["duplicate"]
        check("新闻站有入库也有重复", news_inserted > 0 and news_dup >= 1,
              f"inserted={news_inserted} dup={news_dup}")
        check("批次计数封闭", sum(run1["counts"][k] for k in
              ("pending", "inserted", "duplicate", "failed", "skipped")) == 16,
              str(run1["counts"]))

        mentions_after_partial = int(db.execute(select(func.count(Mention.id))).scalar_one())
        check("部分成功已落库", mentions_after_partial == mentions_before + news_inserted,
              f"{mentions_before} -> {mentions_after_partial}")

        # 台账 vs mentions 对账
        recon1 = svc.reconciliation(db, batch_id)
        check("部分态对账一致", recon1["matched"], str(recon1))
        # 中断源候选已逐条留痕 failed：批次视角台账无 pending（来源行状态才是断点）
        check("部分态批次台账无待处理", recon1["closed"] is True)
        check("部分态仍有失败来源", recon1["ledger"]["failed"] == 8)

        # 入库提及均有情感分
        scored = int(db.execute(
            select(func.count(SentimentScore.id))
            .join(Mention, Mention.id == SentimentScore.mention_id)
            .where(Mention.collect_batch_id == __import__("uuid").UUID(batch_id))
        ).scalar_one())
        check("新提及全部已情感打分", scored == news_inserted, f"scored={scored}")

        # ---- 场景 2：恢复来源后续跑（断点续跑，只处理失败来源）----
        gateway.clear_outage("microblog")
        run2 = svc.run_batch(db, admin, batch_id, trace_id="e2e-2")
        check("续跑后批次 completed", run2["status"] == BATCH_COMPLETED, run2["status"])
        src_map2 = {s["source_code"]: s for s in run2["sources"]}
        check("微博来源续跑成功", src_map2["microblog"]["status"] == SOURCE_SUCCESS)
        check("微博尝试次数=2", src_map2["microblog"]["attempts"] == 2,
              str(src_map2["microblog"]["attempts"]))
        check("新闻站未重放(attempts=1)", src_map2["news_wire"]["attempts"] == 1)
        check("续跑后 pending=0", run2["counts"]["pending"] == 0, str(run2["counts"]))
        check("计数封闭=16",
              sum(run2["counts"][k] for k in ("inserted", "duplicate", "failed", "skipped")) == 16)
        check("情感已同步", run2["sentiment_synced"] is True)
        check("爆发统计已同步", run2["burst_synced"] is True, f"events={run2['burst_events']}")

        total_inserted = run2["counts"]["inserted"]
        total_dup = run2["counts"]["duplicate"]
        check("整批含重复判定（seed 已入库 2 条）", total_dup >= 1, f"dup={total_dup}")
        mentions_done = int(db.execute(select(func.count(Mention.id))).scalar_one())
        check("库内增量=批次入库数", mentions_done == mentions_before + total_inserted,
              f"{mentions_before}+{total_inserted} vs {mentions_done}")
        recon2 = svc.reconciliation(db, batch_id)
        check("完成态对账一致且封闭", recon2["matched"] and recon2["closed"], str(recon2))

        # ---- 场景 3：重复运行已完成批次，零新增 ----
        run3 = svc.run_batch(db, admin, batch_id, trace_id="e2e-3")
        check("重复运行仍 completed", run3["status"] == BATCH_COMPLETED)
        check("重复运行入库数不变", run3["counts"]["inserted"] == total_inserted)
        mentions_rerun = int(db.execute(select(func.count(Mention.id))).scalar_one())
        check("重复运行零新增提及", mentions_rerun == mentions_done)

        # ---- 场景 4：同窗口再建批次，全部重复 ----
        second = svc.create_batch(
            db, admin,
            brand_key="coffee",
            source_codes=SOURCES,
            window_start=WS,
            window_end=WE,
            trace_id="e2e-4",
        )
        second_run = svc.run_batch(db, admin, second["id"], trace_id="e2e-4")
        check("第二批零入库", second_run["counts"]["inserted"] == 0, str(second_run["counts"]))
        check("第二批全重复", second_run["counts"]["duplicate"] == 16)
        mentions_second = int(db.execute(select(func.count(Mention.id))).scalar_one())
        check("第二批零新增提及", mentions_second == mentions_done)
        check("第二批批次号不同", second["batch_no"] != run2["batch_no"],
              f"{second['batch_no']} vs {run2['batch_no']}")

        # ---- 场景 5：台账明细接口与页面数字一致 ----
        page = svc.items(db, batch_id, source_code=None, status=None, limit=100, offset=0)
        check("台账行数=16", page["total"] == 16)
        status_counter: dict[str, int] = {}
        for row in page["items"]:
            status_counter[row["status"]] = status_counter.get(row["status"], 0) + 1
        check("台账明细聚合=页面数字",
              status_counter.get(ITEM_INSERTED, 0) == total_inserted
              and status_counter.get(ITEM_DUPLICATE, 0) == total_dup,
              str(status_counter))
        inserted_rows = svc.items(db, batch_id, source_code=None, status=ITEM_INSERTED,
                                  limit=100, offset=0)
        check("已入库条目均带 mention_id",
              all(row["mention_id"] for row in inserted_rows["items"]))

        # ---- 场景 6：空候选报错 ----
        from src.utils.errors import AppError
        try:
            svc.create_batch(
                db, admin,
                brand_key="coffee",
                source_codes=("video_agg",),
                window_start=WS,
                window_end=WE,
            )
            check("空候选被拒绝", False)
        except AppError as exc:
            check("空候选被拒绝", exc.code == "COLLECT_EMPTY", exc.code)

    print()
    if failures:
        print(f"E2E RESULT: {len(failures)} FAIL -> {failures}")
        return 1
    print("E2E RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
