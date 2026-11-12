"""补采来源网关：把确定性语料按 (品牌, 来源, 时间段) 切片，并模拟来源中断。

生产环境这里会换成真实抓取客户端；演示环境用 inbox 语料 + 进程内故障开关，
让「某来源中断 → 批次部分失败 → 断点续跑 → 重试只处理失败来源」可以端到端演示。

故障注入只在显式调用 set_outage 时生效（运维/演示接口），默认全部来源在线。
"""
from __future__ import annotations

import threading
from datetime import datetime

from src.constants.sources import SOURCE_CODES
from src.services.fixtures_loader import inbox_corpus


class SourceUnavailableError(RuntimeError):
    """来源暂不可用（网关级中断）：整源标记 failed，等待续跑重试。"""


class SourceGateway:
    """无状态抓取 + 进程内故障表（线程安全，仅演示用途）。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._outages: dict[str, str] = {}

    def set_outage(self, source_code: str, reason: str = "simulated outage") -> None:
        with self._lock:
            self._outages[source_code] = reason

    def clear_outage(self, source_code: str) -> None:
        with self._lock:
            self._outages.pop(source_code, None)

    def outage_reason(self, source_code: str) -> str | None:
        with self._lock:
            return self._outages.get(source_code)

    def health(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "code": code,
                    "online": code not in self._outages,
                    "reason": self._outages.get(code, ""),
                }
                for code in SOURCE_CODES
            ]

    def fetch(
        self,
        *,
        brand_key: str,
        source_code: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[dict]:
        """拉取窗口内候选；来源处于中断态时抛 SourceUnavailableError。"""
        reason = self.outage_reason(source_code)
        if reason is not None:
            raise SourceUnavailableError(f"来源 {source_code} 暂不可用：{reason}")
        return [
            item
            for item in inbox_corpus()
            if item["brand_key"] == brand_key
            and item["source_code"] == source_code
            and window_start <= item["published_at"] < window_end
        ]


gateway = SourceGateway()
