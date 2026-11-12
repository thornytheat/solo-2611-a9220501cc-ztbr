from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import sentiment_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(tags=["sentiment"])


@router.post("/sentiment/rescore")
def rescore(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sentiment:rescore")),
    _: None = rate_limit("detect"),
) -> dict:
    return sentiment_controller.rescore(db, user, getattr(request.state, "trace_id", ""))


@router.get("/sentiment/summary")
def summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sentiment:read")),
) -> dict:
    return sentiment_controller.summary(db, user)
