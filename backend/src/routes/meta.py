from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import meta_controller
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(tags=["meta"])


@router.get("/meta/bootstrap")
def bootstrap(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("meta:read")),
) -> dict:
    return meta_controller.bootstrap(db, user)


@router.get("/meta/dictionary")
def dictionary(user: User = Depends(require_permission("meta:read"))) -> dict:
    return meta_controller.dictionary()
