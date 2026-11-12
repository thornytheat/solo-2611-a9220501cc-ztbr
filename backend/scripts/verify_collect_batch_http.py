"""补采批次 HTTP 接口端到端测试（FastAPI TestClient + 真实 Postgres，绕过 Redis 限流）。

需要环境变量 DB_HOST/DB_PORT 指向可用 Postgres；本脚本由开发者手动运行，
不进默认 pytest 套件（默认套件只测纯函数，不依赖外部服务）。
"""
from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from src.config.app import create_app
from src.middlewares import rate_limit as rate_limit_mod
from src.services.analysis.source_gateway import gateway

# 本地无 Redis：限流依赖改为直通
rate_limit_mod.check_rate = lambda *args, **kwargs: None  # type: ignore[assignment]

app = create_app()
client = TestClient(app)

WS = "2026-11-05T00:00:00+08:00"
WE = "2026-11-13T00:00:00+08:00"
failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        failures.append(name)


def main() -> int:
    # 网关复位
    for code in ("news_wire", "microblog", "vertical_forum", "video_agg"):
        gateway.clear_outage(code)

    login = client.post(
        "/api/auth/login", json={"email": "admin@newssweep.io", "password": "Demo@2026"}
    )
    check("管理员登录", login.status_code == 200, str(login.status_code))
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 参数校验：空来源
    bad = client.post(
        "/api/collect/batches",
        headers=headers,
        json={"brand_key": "coffee", "source_codes": [], "window_start": WS, "window_end": WE},
    )
    check("空来源 422", bad.status_code == 422, str(bad.status_code))

    # 参数校验：非法品牌
    bad2 = client.post(
        "/api/collect/batches",
        headers=headers,
        json={
            "brand_key": "nope",
            "source_codes": ["news_wire"],
            "window_start": WS,
            "window_end": WE,
        },
    )
    check("非法品牌 422", bad2.status_code == 422)

    # 注入中断 → 创建并运行
    client.post(
        "/api/collect/source-health/microblog?online=false&reason=http-outage",
        headers=headers,
    )
    created = client.post(
        "/api/collect/batches",
        headers=headers,
        json={
            "brand_key": "coffee",
            "source_codes": ["news_wire", "microblog"],
            "window_start": WS,
            "window_end": WE,
        },
    )
    check("创建批次 200", created.status_code == 200, str(created.status_code))
    batch = created.json()
    batch_id = batch["id"]
    check("批次待处理", batch["status"] == "pending")
    check("待处理数=候选数", batch["counts"]["pending"] == batch["counts"]["total"] == 16)

    run1 = client.post(f"/api/collect/batches/{batch_id}/run", headers=headers)
    r1 = run1.json()
    check("首跑部分失败", r1["status"] == "partial", r1["status"])
    src1 = {s["source_code"]: s for s in r1["sources"]}
    check("首跑微博失败", src1["microblog"]["status"] == "failed")
    check("首跑新闻站成功", src1["news_wire"]["status"] == "success")

    # 列表接口
    listing = client.get("/api/collect/batches?limit=10", headers=headers)
    check("批次列表含新批次", any(b["id"] == batch_id for b in listing.json()["items"]))

    # 台账明细：失败来源过滤
    failed_items = client.get(
        f"/api/collect/batches/{batch_id}/items?status=failed&limit=100", headers=headers
    )
    check("失败台账 8 条", failed_items.json()["total"] == 8, str(failed_items.json()["total"]))

    # 对账
    recon = client.get(f"/api/collect/batches/{batch_id}/reconciliation", headers=headers).json()
    check("部分态对账一致", recon["matched"] is True, str(recon))

    # 恢复来源后续跑
    client.post("/api/collect/source-health/microblog?online=true", headers=headers)
    run2 = client.post(f"/api/collect/batches/{batch_id}/run", headers=headers).json()
    check("续跑完成", run2["status"] == "completed", run2["status"])
    check("续跑无待处理", run2["counts"]["pending"] == 0)
    check("情感已同步", run2["sentiment_synced"] is True)
    check("爆发已同步", run2["burst_synced"] is True, f"events={run2['burst_events']}")

    # 详情回看每个来源
    detail = client.get(f"/api/collect/batches/{batch_id}", headers=headers).json()
    check("回看含两个来源", len(detail["sources"]) == 2)
    check(
        "来源计数之和=总数",
        sum(s["counts"]["total"] for s in detail["sources"]) == detail["counts"]["total"],
    )
    for source in detail["sources"]:
        check(
            f"来源 {source['source_code']} 计数封闭",
            sum(source["counts"][k] for k in ("pending", "inserted", "duplicate", "failed", "skipped"))
            == source["counts"]["total"],
            str(source["counts"]),
        )

    # 已入库明细可反查 mention
    inserted = client.get(
        f"/api/collect/batches/{batch_id}/items?status=inserted&limit=100", headers=headers
    ).json()
    check("已入库条目带 mention_id", all(i["mention_id"] for i in inserted["items"]))
    check(
        "入库明细数=页面入库数",
        inserted["total"] == detail["counts"]["inserted"],
        f"{inserted['total']} vs {detail['counts']['inserted']}",
    )
    # 反查提及详情可访问
    mid = inserted["items"][0]["mention_id"]
    mention_resp = client.get(f"/api/mentions/{mid}", headers=headers)
    check("反查提及详情 200", mention_resp.status_code == 200, str(mention_resp.status_code))
    check(
        "新提及带情感分",
        mention_resp.json()["sentiment"]["algorithm_version"] == "sent-1.0.0",
    )

    # 重复运行已完成批次：零新增
    run3 = client.post(f"/api/collect/batches/{batch_id}/run", headers=headers).json()
    check("重复运行仍完成", run3["status"] == "completed")
    check("重复运行入库数不变", run3["counts"]["inserted"] == detail["counts"]["inserted"])

    # 最终对账
    final_recon = client.get(
        f"/api/collect/batches/{batch_id}/reconciliation", headers=headers
    ).json()
    check("最终对账一致且封闭", final_recon["matched"] and final_recon["closed"], str(final_recon))

    # 越权：client 不能访问采集批次接口
    client_login = client.post(
        "/api/auth/login", json={"email": "client@newssweep.io", "password": "Demo@2026"}
    )
    client_headers = {"Authorization": f"Bearer {client_login.json()['token']}"}
    forbidden = client.get("/api/collect/batches", headers=client_headers)
    check("品牌方无权访问批次", forbidden.status_code == 403, str(forbidden.status_code))

    print()
    if failures:
        print(f"HTTP E2E RESULT: {len(failures)} FAIL -> {failures}")
        return 1
    print("HTTP E2E RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
