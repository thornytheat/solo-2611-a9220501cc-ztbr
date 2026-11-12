from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import auth_controller
from src.middlewares.auth import get_current_user
from src.models.user import User
from src.schemas.auth import LoginRequest

router = APIRouter(tags=["auth"])


@router.post("/auth/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    trace_id = getattr(request.state, "trace_id", "")
    return auth_controller.login(db, payload, trace_id)


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return auth_controller.me(user)
