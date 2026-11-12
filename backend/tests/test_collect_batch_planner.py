"""补采批次规划 / 来源网关的纯函数测试（不连数据库）。

覆盖：
- 候选切片严格按品牌 / 来源 / 时间窗口过滤，顺序稳定可复现；
- 来源计划与台账口径一致（台账行数 = 候选数 = 各来源 candidates 之和）；
- 台账封闭口径：终态计数之和等于行数、pending 归零；
- 网关故障开关只影响被注入的来源，恢复后立即可用；
- failed 不是来源终态（可重试断点），success 才是。
"""
from __future__ import annotations

from datetime import datetime

import pytest

from src.models.collect_batch import (
    ITEM_DUPLICATE,
    ITEM_FAILED,
    ITEM_INSERTED,
    ITEM_PENDING,
    ITEM_SKIPPED,
    SOURCE_FAILED,
    SOURCE_FINAL_STATUSES,
    SOURCE_PENDING,
    SOURCE_SUCCESS,
)
from src.services.analysis.collect_planner import (
    build_item_ledger,
    build_source_plan,
    ledger_is_closed,
    reconcile_totals,
    select_candidates,
    split_by_source,
)
from src.services.analysis.source_gateway import SourceGateway, SourceUnavailableError
from src.services.fixtures_loader import inbox_corpus
from src.utils.timeutil import TZ_SHANGHAI

WS = datetime(2026, 11, 5, 0, 0, tzinfo=TZ_SHANGHAI)
WE = datetime(2026, 11, 13, 0, 0, tzinfo=TZ_SHANGHAI)
ALL_GROUPS = frozenset(
    {
        "coffee-foreign",
        "coffee-taste",
        "maternal-quality",
        "maternal-service",
        "outdoor-durability",
        "outdoor-price",
        "pet-safety",
        "pet-formula",
        "homecare-effect",
        "homecare-packaging",
        "snack-additive",
        "snack-taste",
    }
)


def test_select_candidates_filters_by_brand_source_window() -> None:
    sources = ("news_wire", "microblog")
    selected = select_candidates(
        inbox_corpus(),
        brand_key="coffee",
        source_codes=sources,
        window_start=WS,
        window_end=WE,
        enabled_group_codes=ALL_GROUPS,
    )
    assert selected  # 非空
    for item in selected:
        assert item["brand_key"] == "coffee"
        assert item["source_code"] in sources
        assert WS <= item["published_at"] < WE

    # 窗口边界：上含下不含
    edge = select_candidates(
        inbox_corpus(),
        brand_key="coffee",
        source_codes=sources,
        window_start=WE,
        window_end=datetime(2026, 11, 20, 0, 0, tzinfo=TZ_SHANGHAI),
        enabled_group_codes=ALL_GROUPS,
    )
    assert edge == []


def test_select_candidates_is_deterministic_and_sorted() -> None:
    kwargs = dict(
        brand_key="maternal",
        source_codes=("news_wire", "microblog", "vertical_forum", "video_agg"),
        window_start=WS,
        window_end=WE,
        enabled_group_codes=ALL_GROUPS,
    )
    first = select_candidates(inbox_corpus(), **kwargs)
    second = select_candidates(inbox_corpus(), **kwargs)
    assert [i["external_id"] for i in first] == [i["external_id"] for i in second]
    keys = [(i["source_code"], i["published_at"], i["external_id"]) for i in first]
    assert keys == sorted(keys)


def test_plan_and_ledger_share_one_consistent_caliber() -> None:
    sources = ("news_wire", "microblog", "vertical_forum", "video_agg")
    candidates = select_candidates(
        inbox_corpus(),
        brand_key="pet",
        source_codes=sources,
        window_start=WS,
        window_end=WE,
        enabled_group_codes=ALL_GROUPS,
    )
    plan = build_source_plan(candidates, sources)
    ledger = build_item_ledger(candidates)

    assert len(ledger) == len(candidates)
    assert sum(row["candidates"] for row in plan) == len(candidates)
    assert [row["source_code"] for row in plan] == list(sources)
    assert all(row["status"] == SOURCE_PENDING for row in plan)
    assert all(row["status"] == ITEM_PENDING for row in ledger)
    # 台账 position 连续
    assert [row["position"] for row in ledger] == list(range(len(ledger)))

    buckets = split_by_source(candidates, sources)
    for row in plan:
        assert row["candidates"] == len(buckets[row["source_code"]])


def test_reconcile_totals_and_closed_invariant() -> None:
    rows = [
        {"status": ITEM_INSERTED},
        {"status": ITEM_INSERTED},
        {"status": ITEM_DUPLICATE},
        {"status": ITEM_FAILED},
        {"status": ITEM_SKIPPED},
    ]
    totals = reconcile_totals(rows)
    assert totals == {"inserted": 2, "duplicate": 1, "failed": 1, "skipped": 1, "pending": 0}
    assert ledger_is_closed(rows) is True

    open_rows = rows + [{"status": ITEM_PENDING}]
    assert ledger_is_closed(open_rows) is False


def test_disabled_group_candidates_are_still_in_scope() -> None:
    # 停用组不把候选剔除，只是后续处理时计入 skipped（口径不丢条目）
    selected = select_candidates(
        inbox_corpus(),
        brand_key="coffee",
        source_codes=("news_wire", "microblog"),
        window_start=WS,
        window_end=WE,
        enabled_group_codes=frozenset({"coffee-foreign"}),
    )
    assert any(not item["group_enabled"] for item in selected)
    assert all(item["group_code"] in {"coffee-foreign", "coffee-taste"} for item in selected)


def test_source_gateway_outage_is_scoped_and_recoverable() -> None:
    gateway = SourceGateway()
    gateway.set_outage("microblog", "unit outage")
    health = {item["code"]: item for item in gateway.health()}
    assert health["microblog"]["online"] is False
    assert all(health[c]["online"] for c in health if c != "microblog")

    with pytest.raises(SourceUnavailableError):
        gateway.fetch(
            brand_key="coffee",
            source_code="microblog",
            window_start=WS,
            window_end=WE,
        )
    # 未受影响来源仍可抓取
    ok = gateway.fetch(
        brand_key="coffee",
        source_code="news_wire",
        window_start=WS,
        window_end=WE,
    )
    assert isinstance(ok, list)

    gateway.clear_outage("microblog")
    assert gateway.outage_reason("microblog") is None
    recovered = gateway.fetch(
        brand_key="coffee",
        source_code="microblog",
        window_start=WS,
        window_end=WE,
    )
    assert isinstance(recovered, list)


def test_failed_source_is_retryable_not_terminal() -> None:
    # 关键状态机约束：failed 必须能被续跑选中，只有 success 不可重放
    assert SOURCE_SUCCESS in SOURCE_FINAL_STATUSES
    assert SOURCE_FAILED not in SOURCE_FINAL_STATUSES
    assert SOURCE_PENDING not in SOURCE_FINAL_STATUSES
