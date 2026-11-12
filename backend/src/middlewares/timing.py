"""计时中间件：把本次请求耗时与算法耗时写进 x-elapsed-ms，前端顶栏展示。"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["x-elapsed-ms"] = str(int((time.perf_counter() - started) * 1000))
        return response
