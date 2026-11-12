"""pytest 根配置：只做 sys.path 兜底，不连 DB / 不连 Redis / 不起 Web 进程。

被测对象全部是纯函数：
- `src.services.analysis.sentiment_analyzer`（算法 1：中文情感打分）
- `src.services.analysis.burst_detector`（算法 2：小时桶爆发检测）
- `src.services.analysis.lexicon` / `src.services.analysis.dedupe`
- `src.utils.textutils` / `src.utils.timeutil`（归一化与时间工具）
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
