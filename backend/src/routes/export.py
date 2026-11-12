from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import export_controller
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(tags=["export"])


@router.get("/export/daily")
def daily(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("export:daily")),
) -> dict:
    return export_controller.daily(db, user, getattr(request.state, "trace_id", ""))


@router.get("/export/preview")
def preview(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("export:daily")),
) -> dict:
    return export_controller.preview(db, user)
