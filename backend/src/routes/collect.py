from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import collect_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(tags=["collect"])


@router.post("/collect/run")
def run_collection(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("collect:run")),
    _: None = rate_limit("collect"),
) -> dict:
    return collect_controller.run(db, user, getattr(request.state, "trace_id", ""))


@router.get("/collect/runs")
def runs(
    limit: int = Query(default=8, ge=1, le=30),
    db: Session = Depends(get_db),
    # 采集运行记录含全局扫描/入库量与操作人邮箱（内部备注），品牌方只读角色不可见。
    user: User = Depends(require_permission("collect:run")),
) -> dict:
    return collect_controller.runs(db, limit)
