"""RBAC 角色与能力矩阵（前后端一致：roles.ts 为镜像）。"""
from __future__ import annotations

from src.constants.enums import UserRole

ROLE_ADMIN = UserRole.ADMIN.value
ROLE_ANALYST = UserRole.ANALYST.value
ROLE_CLIENT = UserRole.CLIENT.value

ALL_ROLES: tuple[str, ...] = (ROLE_ADMIN, ROLE_ANALYST, ROLE_CLIENT)
STAFF_ROLES: tuple[str, ...] = (ROLE_ADMIN, ROLE_ANALYST)

PERMISSIONS: dict[str, tuple[str, ...]] = {
    # 阅读（client 只能读自己品牌，服务层做品牌域裁剪）
    "mentions:read": ALL_ROLES,
    "groups:read": ALL_ROLES,
    "bursts:read": ALL_ROLES,
    "sentiment:read": ALL_ROLES,
    "meta:read": ALL_ROLES,
    # 值班动作
    "mentions:review": STAFF_ROLES,
    "collect:run": STAFF_ROLES,
    "sentiment:rescore": STAFF_ROLES,
    "bursts:detect": STAFF_ROLES,
    "bursts:claim": STAFF_ROLES,
    "bursts:dispose": STAFF_ROLES,
    "groups:trial": STAFF_ROLES,
    "export:daily": STAFF_ROLES,
    # 总监动作
    "groups:write": (ROLE_ADMIN,),
    "settings:write": (ROLE_ADMIN,),
    "audit:read": (ROLE_ADMIN,),
}

ROLE_SCOPE: dict[str, str] = {
    ROLE_ADMIN: "关键词组与词典 · 阈值 · 发布日报",
    ROLE_ANALYST: "采集 · 情感复核 · 预警认领处置",
    ROLE_CLIENT: "只读自己品牌（不含内部备注与处置记录）",
}


def role_can(role: str, action: str) -> bool:
    return role in PERMISSIONS.get(action, ())


def role_permissions(role: str) -> list[str]:
    return [action for action, roles in PERMISSIONS.items() if role in roles]


def role_scope(role: str) -> str:
    """角色的一句话职责（前端 AppShell / 登录页展示）。"""
    return ROLE_SCOPE.get(role, "")
