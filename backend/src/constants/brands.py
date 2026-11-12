"""6 个被服务品牌的目录（品牌方账号按 brand_key 做数据域裁剪）。"""
from __future__ import annotations

from src.constants.enums import BrandKey

BRAND_CATALOG: list[dict] = [
    {
        "key": BrandKey.COFFEE.value,
        "name": "澄野咖啡",
        "short": "澄野",
        "category": "即饮咖啡 / 挂耳",
        "since": "2019",
        "scene": "便利店冷柜 + 电商旗舰店",
        "client_email": "client@newssweep.io",
    },
    {
        "key": BrandKey.MATERNAL.value,
        "name": "芽初母婴",
        "short": "芽初",
        "category": "婴儿辅食 / 洗护",
        "since": "2017",
        "scene": "母婴连锁 + 内容电商",
    },
    {
        "key": BrandKey.OUTDOOR.value,
        "name": "岩行户外",
        "short": "岩行",
        "category": "轻户外装备",
        "since": "2020",
        "scene": "垂类电商 + 线下体验店",
    },
    {
        "key": BrandKey.PET.value,
        "name": "毛球宠物",
        "short": "毛球",
        "category": "主粮 / 零食",
        "since": "2018",
        "scene": "宠物店 + 电商",
    },
    {
        "key": BrandKey.HOMECARE.value,
        "name": "净川家清",
        "short": "净川",
        "category": "家清日化",
        "since": "2016",
        "scene": "商超 + 直播",
    },
    {
        "key": BrandKey.SNACK.value,
        "name": "脆岛零食",
        "short": "脆岛",
        "category": "膨化 / 烘焙零食",
        "since": "2021",
        "scene": "量贩零食店 + 电商",
    },
]

BRAND_KEYS: tuple[str, ...] = tuple(item["key"] for item in BRAND_CATALOG)


def brand_meta(key: str) -> dict | None:
    for item in BRAND_CATALOG:
        if item["key"] == key:
            return item
    return None
