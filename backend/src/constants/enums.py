"""共享枚举（后端定义，前端 frontend/src/constants/enums.ts 必须一致）。

README「枚举出现位置」列出全部使用点。
"""
from __future__ import annotations

from enum import Enum


class SentimentLabel(str, Enum):
    """情感标签（算法输出）。"""

    POS = "pos"
    NEU = "neu"
    NEG = "neg"


class BurstLevel(str, Enum):
    """爆发等级（按 z 分档）。"""

    WATCH = "watch"
    ALERT = "alert"
    CRITICAL = "critical"


class BurstStatus(str, Enum):
    """爆发事件处置状态。"""

    OPEN = "open"
    CLAIMED = "claimed"
    HANDLED = "handled"
    DISMISSED = "dismissed"


class ReviewStatus(str, Enum):
    """情感复核状态。"""

    AUTO = "auto"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"


class SourceCode(str, Enum):
    """4 个采集来源。"""

    NEWS_WIRE = "news_wire"
    MICROBLOG = "microblog"
    VERTICAL_FORUM = "vertical_forum"
    VIDEO_AGG = "video_agg"


class BrandKey(str, Enum):
    """6 个被服务品牌。"""

    COFFEE = "coffee"
    MATERNAL = "maternal"
    OUTDOOR = "outdoor"
    PET = "pet"
    HOMECARE = "homecare"
    SNACK = "snack"


class UserRole(str, Enum):
    """角色。"""

    ADMIN = "admin"
    ANALYST = "analyst"
    CLIENT = "client"


SENTIMENT_LABELS: dict[str, str] = {
    SentimentLabel.POS.value: "正面",
    SentimentLabel.NEU.value: "中性",
    SentimentLabel.NEG.value: "负面",
}

BURST_LEVEL_LABELS: dict[str, str] = {
    BurstLevel.WATCH.value: "关注",
    BurstLevel.ALERT.value: "预警",
    BurstLevel.CRITICAL.value: "危急",
}

BURST_STATUS_LABELS: dict[str, str] = {
    BurstStatus.OPEN.value: "待认领",
    BurstStatus.CLAIMED.value: "已认领",
    BurstStatus.HANDLED.value: "已处置",
    BurstStatus.DISMISSED.value: "已排除",
}

REVIEW_STATUS_LABELS: dict[str, str] = {
    ReviewStatus.AUTO.value: "机器判定",
    ReviewStatus.PENDING.value: "待复核",
    ReviewStatus.CONFIRMED.value: "复核确认",
    ReviewStatus.CORRECTED.value: "人工修正",
}

BRAND_LABELS: dict[str, str] = {
    BrandKey.COFFEE.value: "澄野咖啡",
    BrandKey.MATERNAL.value: "芽初母婴",
    BrandKey.OUTDOOR.value: "岩行户外",
    BrandKey.PET.value: "毛球宠物",
    BrandKey.HOMECARE.value: "净川家清",
    BrandKey.SNACK.value: "脆岛零食",
}

SOURCE_LABELS: dict[str, str] = {
    SourceCode.NEWS_WIRE.value: "新闻站",
    SourceCode.MICROBLOG.value: "微博式社区",
    SourceCode.VERTICAL_FORUM.value: "垂直论坛",
    SourceCode.VIDEO_AGG.value: "短视频标题聚合",
}

ROLE_LABELS: dict[str, str] = {
    UserRole.ADMIN.value: "舆情总监",
    UserRole.ANALYST.value: "值班分析师",
    UserRole.CLIENT.value: "品牌方",
}
