"""演示语料（确定性）：12 组关键词 × 900 条提及 × 4 个来源 × 92 条采集候选。

设计约束（与 batch-plan §5.2 对齐）：
- 6 个品牌各 2 组关键词 = 12 组；
- 900 条提及：正 512 / 中 241 / 负 147，逐条由 `sentiment_analyzer` 真算得出，本文件只提供文本；
- 小时分布是显式表：`HOUR_PLAN` 给出「过去 7 天同小时基线 + 评估日计数」，
  其中 coffee-foreign@14 的基线序列固定为 (0,1,3,4,8,9,9)，评估日 31 条 → z=7.42（critical）；
- 其余候选（92 条）是「补采窗口」原始条目，seed 里已入库 6 条 → 采集运行命中 6 条重复、86 条新增。

本文件不含任何随机数：所有下标都由 (组序号, 条目序号) 决定。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.config.settings import settings
from src.constants.brands import BRAND_CATALOG
from src.constants.enums import SourceCode
from src.services.analysis.dedupe import content_hash
from src.utils.timeutil import TZ_SHANGHAI, parse_seed_now

SEED_ANCHOR = parse_seed_now(settings.seed_now)
EVAL_DAY = SEED_ANCHOR.date()
DEMO_PASSWORD = "Demo@2026"
LABEL = "newssweep"

DEMO_USERS: list[tuple[str, str, str, str | None]] = [
    ("admin@newssweep.io", "罗青 · 舆情总监", "admin", None),
    ("analyst@newssweep.io", "祁舟 · 值班分析师", "analyst", None),
    ("client@newssweep.io", "澄野咖啡 · 品牌市场部", "client", "coffee"),
]

# --------------------------------------------------------------- 关键词组 ----

GROUP_SPECS: list[dict] = [
    {
        "code": "coffee-foreign",
        "name": "咖啡-异物",
        "brand_key": "coffee",
        "keywords": ["异物", "杂质", "塑料", "虫"],
        "synonyms": ["澄野异物", "咖啡里喝出东西", "混进异物", "沉淀物"],
        "excludes": ["咖啡渣", "滤纸", "研磨度"],
        "priority": 9,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "重点组：任何异物类提及都必须 30 分钟内进入人工复核。",
    },
    {
        "code": "coffee-taste",
        "name": "咖啡-口感",
        "brand_key": "coffee",
        "keywords": ["口感", "回甘", "酸味", "苦涩"],
        "synonyms": ["味道怪", "不好喝", "寡淡", "焦苦"],
        "excludes": ["手冲教程", "器具评测"],
        "priority": 6,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "口感类噪声高，排除词随新品上市周更新。",
    },
    {
        "code": "maternal-quality",
        "name": "母婴-品质",
        "brand_key": "maternal",
        "keywords": ["品质", "成分", "过敏", "质检"],
        "synonyms": ["芽初品质", "宝宝不适", "红屁股", "成分表"],
        "excludes": ["辅食做法", "育儿科普"],
        "priority": 8,
        "z_threshold": 2.5,
        "min_count": 4,
        "owner_note": "母婴类容忍度低，z 阈值下调到 2.5。",
    },
    {
        "code": "maternal-service",
        "name": "母婴-售后",
        "brand_key": "maternal",
        "keywords": ["售后", "退款", "换货", "客服"],
        "synonyms": ["芽初客服", "不给退", "受理慢", "没人管"],
        "excludes": ["门店地址", "营业时间"],
        "priority": 5,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "",
    },
    {
        "code": "outdoor-durability",
        "name": "户外-耐用",
        "brand_key": "outdoor",
        "keywords": ["耐用", "开线", "断裂", "防水"],
        "synonyms": ["岩行开裂", "用两次就坏", "不结实", "拉链坏"],
        "excludes": ["徒步路线", "装备测评"],
        "priority": 7,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "耐用类与「测评」噪声需排除词隔离。",
    },
    {
        "code": "outdoor-price",
        "name": "户外-涨价",
        "brand_key": "outdoor",
        "keywords": ["涨价", "价格", "促销", "折扣"],
        "synonyms": ["岩行贵了", "抄底", "降价款", "价格刺客"],
        "excludes": ["汇率", "原材料行情"],
        "priority": 6,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "大促前后每组日均 2-3 条，注意区分真涨价与促销讨论。",
    },
    {
        "code": "pet-safety",
        "name": "宠物-安全",
        "brand_key": "pet",
        "keywords": ["安全", "中毒", "便血", "呕吐"],
        "synonyms": ["毛球吃了不适", "猫粮问题", "狗粮异味", "送医"],
        "excludes": ["养宠科普", "领养信息"],
        "priority": 9,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "最高优先级：涉及宠物就医的提及直接升级人工电话回访。",
    },
    {
        "code": "pet-formula",
        "name": "宠物-配方",
        "brand_key": "pet",
        "keywords": ["配方", "肉含量", "添加剂", "粗蛋白"],
        "synonyms": ["毛球配方", "换粮", "成分争议", "谷物"],
        "excludes": ["自制猫饭", "生骨肉教程"],
        "priority": 5,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "",
    },
    {
        "code": "homecare-effect",
        "name": "家清-效果",
        "brand_key": "homecare",
        "keywords": ["效果", "去污", "残留", "味道"],
        "synonyms": ["净川洗不干净", "泡沫多", "香精味", "复洗"],
        "excludes": ["家务技巧", "洗衣机维修"],
        "priority": 6,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "",
    },
    {
        "code": "homecare-packaging",
        "name": "家清-包装",
        "brand_key": "homecare",
        "keywords": ["包装", "漏液", "瓶身", "泵头"],
        "synonyms": ["净川漏了", "压不出来", "瓶子变形", "运输破损"],
        "excludes": ["空瓶回收", "分装瓶"],
        "priority": 4,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "",
    },
    {
        "code": "snack-additive",
        "name": "零食-添加剂",
        "brand_key": "snack",
        "keywords": ["添加剂", "防腐剂", "代可可脂", "香精"],
        "synonyms": ["脆岛配料表", "科技与狠活", "反式脂肪", "配料争议"],
        "excludes": ["食品科普", "配料表怎么看"],
        "priority": 8,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "配料表话题易被搬运号放大，注意同源转载去重。",
    },
    {
        "code": "snack-taste",
        "name": "零食-口味",
        "brand_key": "snack",
        "keywords": ["口味", "太甜", "油味", "酥脆"],
        "synonyms": ["脆岛难吃", "齁甜", "油耗味", "不够脆"],
        "excludes": ["零食测评合集", "自制零食"],
        "priority": 5,
        "z_threshold": 3.0,
        "min_count": 5,
        "owner_note": "",
    },
]

GROUP_CODES: tuple[str, ...] = tuple(spec["code"] for spec in GROUP_SPECS)
GROUP_INDEX: dict[str, int] = {spec["code"]: i for i, spec in enumerate(GROUP_SPECS)}
BRAND_BY_GROUP: dict[str, str] = {spec["code"]: spec["brand_key"] for spec in GROUP_SPECS}
BRAND_SHORT: dict[str, str] = {item["key"]: item["short"] for item in BRAND_CATALOG}

# 每组情感类别人数：正 / 中 / 负（合计 900，正 512 中 241 负 147）
CLASS_PLAN: dict[str, tuple[int, int, int]] = {
    "coffee-foreign": (55, 22, 48),
    "coffee-taste": (37, 19, 6),
    "maternal-quality": (35, 17, 6),
    "maternal-service": (43, 20, 8),
    "outdoor-durability": (40, 19, 7),
    "outdoor-price": (47, 23, 14),
    "pet-safety": (46, 20, 13),
    "pet-formula": (35, 17, 5),
    "homecare-effect": (47, 21, 6),
    "homecare-packaging": (40, 20, 8),
    "snack-additive": (47, 24, 17),
    "snack-taste": (40, 19, 9),
}

# 小时计划：series = 过去 7 天同小时计数（由远到近），eval = 评估日该小时计数
HOUR_PLAN: dict[str, dict[int, dict]] = {
    "coffee-foreign": {
        9: {"series": [2, 2, 3, 2, 3, 2, 3], "eval": 3},
        14: {"series": [0, 1, 3, 4, 8, 9, 9], "eval": 31},
        20: {"series": [2, 3, 2, 3, 2, 2, 3], "eval": 3},
    },
    "coffee-taste": {
        9: {"series": [1, 2, 1, 2, 1, 2, 1], "eval": 2},
        20: {"series": [2, 1, 2, 1, 2, 1, 2], "eval": 2},
    },
    "maternal-quality": {
        10: {"series": [1, 1, 2, 1, 1, 2, 1], "eval": 2},
        20: {"series": [1, 2, 1, 1, 2, 1, 1], "eval": 1},
    },
    "maternal-service": {
        10: {"series": [2, 2, 2, 3, 2, 2, 3], "eval": 3},
        21: {"series": [2, 2, 3, 2, 2, 3, 2], "eval": 2},
    },
    "outdoor-durability": {
        9: {"series": [1, 2, 2, 1, 2, 2, 1], "eval": 2},
        16: {"series": [2, 1, 2, 2, 1, 2, 2], "eval": 2},
    },
    "outdoor-price": {
        9: {"series": [2, 2, 3, 2, 2, 3, 2], "eval": 7},
        16: {"series": [2, 2, 2, 2, 2, 2, 2], "eval": 2},
    },
    "pet-safety": {
        16: {"series": [1, 1, 2, 1, 1, 2, 1], "eval": 5},
        20: {"series": [2, 2, 3, 2, 2, 2, 2], "eval": 2},
    },
    "pet-formula": {
        10: {"series": [1, 1, 1, 2, 1, 1, 1], "eval": 1},
        20: {"series": [1, 1, 1, 1, 2, 1, 1], "eval": 1},
    },
    "homecare-effect": {
        9: {"series": [2, 2, 3, 2, 3, 2, 3], "eval": 3},
        15: {"series": [2, 2, 2, 2, 2, 2, 2], "eval": 2},
    },
    "homecare-packaging": {
        20: {"series": [2, 2, 2, 3, 2, 2, 2], "eval": 6},
        10: {"series": [1, 2, 1, 2, 1, 2, 1], "eval": 2},
    },
    "snack-additive": {
        10: {"series": [2, 2, 2, 3, 2, 2, 2], "eval": 7},
        14: {"series": [3, 2, 3, 3, 2, 3, 2], "eval": 3},
    },
    "snack-taste": {
        11: {"series": [2, 2, 2, 2, 2, 2, 2], "eval": 2},
        20: {"series": [2, 2, 2, 2, 2, 2, 2], "eval": 2},
    },
}

# 剩余量摊到基线日的这些小时（评估日这些小时为 0，不参与 z 判定）
LEFTOVER_HOURS: tuple[int, ...] = (7, 8, 12, 18, 22, 23)

# 6 条「已入库的补采候选」：external_id 与采集窗口前 6 条重合 → 采集运行命中 6 条重复
SHADOW_SPECS: list[dict] = [
    {
        "external_id": f"inbox:{index:03d}",
        "day_offset": -6 + index,
        "hour": 6,
        "minute": 12 + index * 5,
    }
    for index in range(6)
]

PRODUCTS: dict[str, list[str]] = {
    "coffee": ["挂耳咖啡", "冷萃液", "即饮拿铁"],
    "maternal": ["婴儿米粉", "洗衣皂", "润肤乳"],
    "outdoor": ["冲锋衣", "登山杖", "露营灯"],
    "pet": ["冻干主粮", "鸡肉条", "猫砂"],
    "homecare": ["洗衣凝珠", "厨房清洁剂", "除菌喷雾"],
    "snack": ["薯片", "小圆饼", "海苔脆"],
}

AUTHORS: tuple[str, ...] = (
    "值夜班的猫",
    "南山喝咖啡",
    "小满不加糖",
    "阿岚的厨房",
    "户外老张",
    "毛球家长L",
    "净川用户_882",
    "脆岛囤货王",
    "县城消费者",
    "一杯半",
    "晚风测评",
    "宝妈阿禾",
    "露营的鱼",
    "退货小分队",
    "每周一箱",
    "打工人午饭",
)

SOURCE_DOMAIN = {
    SourceCode.NEWS_WIRE.value: "news.fixture.local",
    SourceCode.MICROBLOG.value: "weibo.fixture.local",
    SourceCode.VERTICAL_FORUM.value: "forum.fixture.local",
    SourceCode.VIDEO_AGG.value: "video.fixture.local",
}

POS_TEMPLATES: tuple[str, ...] = (
    "{brand}{product}开袋就香气很足，回甘明显，已经回购三次了。",
    "这箱{brand}{product}比上次还顺滑，家里人一致好评。",
    "试了{brand}{product}，口感细腻，值得推荐。",
    "{brand}{product}的用料扎实，包装严实，物流也及时，好评。",
    "第一次买{brand}{product}，居然有点惊艳，太喜欢了。",
    "{brand}{product}性价比很划算，一箱到手 39.9，超值。",
    "把{brand}{product}推荐给同事了，大家反馈都不错，准备回购。",
    "{brand}{product}这次升级后稳定不少，客服也专业，点赞。",
    "{brand}{product}的售后到位，换货两天就到，省心又暖心。",
    "连续用了半年{brand}{product}，一直很稳定，靠谱，会继续支持。",
    "{brand}{product}开箱很精致，细节贴心，送人也好看。",
    "给娃买的{brand}{product}，成分天然，用着安心，会回购。",
    "{brand}{product}穿上轻便又舒适，走了一天也不累，结实。",
    "{brand}{product}的耐用度真的可以，摔了两次都没事，结实。",
    "毛球吃{brand}{product}三个月，毛色好看了，健康又营养。",
    "{brand}{product}清洁力不错，一遍就干净，味道也清爽。",
    "{brand}{product}这次配方温和，敏感肌也能用，放心。",
    "囤了三箱{brand}{product}，价格实在，品质稳定，很划算。",
    "{brand}{product}客服及时，态度真诚，问题当天就解决，满意。",
    "{brand}{product}甜度刚好，孩子很喜欢，一致好评。",
)

NEG_TEMPLATES: tuple[str, ...] = (
    "{brand}{product}拆开就有刺鼻异味，袋底还有异物，太失望了！",
    "{brand}{product}这批明显发霉，霉点一片，已经投诉了。",
    "用了{brand}{product}当场拉肚子，怀疑变质，太糟心了！",
    "{brand}{product}口感发酸，还有一股酸败味，难喝。",
    "{brand}{product}包装破损漏液，客服推诿，态度差，差评。",
    "{brand}{product}的批次不合格，检测超标，太危险了！",
    "{brand}{product}用两次就开裂，掉色严重，劣质。",
    "{brand}{product}虚假宣传，配料表造假，智商税。",
    "{brand}{product}卖得比标价贵，缺斤少两，坑人。",
    "{brand}{product}打开是结块，冲出来浑浊，还有霉味。",
    "{brand}{product}让毛球过敏，红肿好几天，太心疼也太生气。",
    "{brand}{product}这次的添加剂话题被曝光，评论区都在抵制。",
    "退货退款被拖延，客服敷衍，维权难，避雷{brand}{product}。",
    "{brand}{product}的塑料片混进粉里，害我呛了半天，恶心！",
    "{brand}{product}里喝出头发丝，商家还推诿，太恶心了。",
)

WIRE_TEMPLATES: tuple[str, ...] = (
    "【通报】监管部门通报某批次{brand}{product}疑似混入异物，企业已启动召回，调查结果待公布。消费者投诉集中在同一产线。",
    "【热线】12315 转办：{brand}{product}异味投诉 3 起，属地市场监管所已到场核查，通报稍后发布。",
)

NEU_TEMPLATES: tuple[str, ...] = (
    "{brand}{product}本月生产批次 B24，规格 250g×12，常温保存。",
    "到货记录：{brand}{product}两箱，生产日期 2026-10-28，保质期 12 个月。",
    "{brand}{product}配料表：咖啡豆、水；含糖 8.2g/100ml。",
    "客服回复：{brand}{product}的发货仓在苏州，三天内出库。",
    "{brand}{product}线下铺货门店已更新到 37 家，含华东 12 家。",
    "关于{brand}{product}的检测报告编号 A2026-1187，可在官网查询。",
    "{brand}{product}换了新包装，净含量不变，零售价 9.9 元。",
    "问一下{brand}{product}的冲煮水温，包装上写 92 度。",
    "{brand}{product}在 11 月的促销档期是 11-15 至 11-20。",
    "{brand}{product}的客服电话 400-880-0000，工作日 9:00-18:00。",
    "整理了一下{brand}{product}近三个月的价格记录，见附表。",
    "{brand}{product}这次上新两个口味：海盐、可可，规格 45g。",
    "会议纪要：{brand}{product}四季度投放预算按渠道拆分。",
    "{brand}{product}的产地是云南保山，海拔 1400 米。",
    "{brand}{product}包装正面印了溯源码，扫码显示批次信息。",
)

TITLES: dict[str, tuple[str, ...]] = {
    "pos": (
        "晒单：这次真的买对了",
        "回购记录 +1",
        "开箱记录：香气在线",
        "同事都在问链接",
        "这一箱可以闭眼入",
    ),
    "neg": (
        "开袋记录：不敢再买了",
        "这批次有问题",
        "售后处理记录（未解决）",
        "先别买，看完这条",
        "客服让我自己承担",
    ),
    "neu": (
        "到货与批次核对",
        "规格与价格记录",
        "客服问询记录",
        "门店铺货进度",
        "四季度渠道排期",
    ),
}

# ------------------------------------------------------------ 计划展开 ----


def _interleave(labels: list[str]) -> list[str]:
    """固定散列置换：正/中/负在时间轴上均匀铺开（无随机数）。"""
    total = len(labels)
    if total == 0:
        return []
    order = sorted(range(total), key=lambda i: ((i * 2654435761) % 4294967291, i))
    out: list[str] = [""] * total
    for slot, src in enumerate(order):
        out[src] = labels[slot]
    return out


def build_hour_plan() -> dict[tuple[str, int, int], int]:
    """(code, day_offset, hour) -> 条数；day_offset 0 = 评估日，-7..-1 = 基线日。"""
    plan: dict[tuple[str, int, int], int] = {}
    for spec in GROUP_SPECS:
        code = spec["code"]
        hours = HOUR_PLAN[code]
        used = 0
        for hour, conf in hours.items():
            for idx, count in enumerate(conf["series"]):
                day_offset = -7 + idx
                if count:
                    plan[(code, day_offset, hour)] = count
                used += count
            if conf["eval"]:
                plan[(code, 0, hour)] = conf["eval"]
            used += conf["eval"]
        # 已入库的补采候选（与采集窗口前 6 条同 external_id）
        if code == "coffee-foreign":
            used += len(SHADOW_SPECS)
        total = sum(CLASS_PLAN[code])
        leftover = total - used
        if leftover < 0:
            raise ValueError(f"组 {code} 的计划超出配额：used={used} total={total}")
        slots = [(day, hour) for day in range(-7, 0) for hour in LEFTOVER_HOURS]
        for index in range(leftover):
            day, hour = slots[index % len(slots)]
            plan[(code, day, hour)] = plan.get((code, day, hour), 0) + 1
    return plan


def _slot_time(day_offset: int, hour: int, minute: int) -> datetime:
    day = EVAL_DAY + timedelta(days=day_offset)
    return datetime(day.year, day.month, day.day, hour, minute, 0, tzinfo=TZ_SHANGHAI)


def _compose(code: str, brand_key: str, product: str, cls: str, index: int, special: str | None) -> tuple[str, str]:
    brand = BRAND_SHORT[brand_key]
    if special == "wire":
        body = WIRE_TEMPLATES[index % len(WIRE_TEMPLATES)].format(brand=brand, product=product)
        title = "通报：疑似异物批次调查进展" if index % 2 == 0 else "热线转办：异味投诉核查"
        return title, body
    pool = {"pos": POS_TEMPLATES, "neg": NEG_TEMPLATES, "neu": NEU_TEMPLATES}[cls]
    template = pool[index % len(pool)]
    body = template.format(brand=brand, product=product)
    titles = TITLES[cls]
    return titles[index % len(titles)], body


def seed_mentions() -> list[dict]:
    """展开成逐条提及（含情感类别与复核标记）。"""
    plan = build_hour_plan()
    mentions: list[dict] = []

    for spec in GROUP_SPECS:
        code = spec["code"]
        brand_key = spec["brand_key"]
        gi = GROUP_INDEX[code]
        slots: list[dict] = []
        for (plan_code, day_offset, hour), count in sorted(plan.items()):
            if plan_code != code:
                continue
            for i in range(count):
                minute = (i * 7 + hour * 3 + gi) % 60
                published = _slot_time(day_offset, hour, minute)
                source = [
                    SourceCode.NEWS_WIRE.value,
                    SourceCode.MICROBLOG.value,
                    SourceCode.VERTICAL_FORUM.value,
                    SourceCode.VIDEO_AGG.value,
                ][(len(slots) + gi) % 4]
                slots.append(
                    {
                        "group_code": code,
                        "brand_key": brand_key,
                        "source_code": source,
                        "published_at": published,
                        "index": len(slots),
                        "day_offset": day_offset,
                        "hour": hour,
                        "forced_label": None,
                        "special": None,
                        "external_id": None,
                    }
                )
        # 6 条已入库的补采候选（与采集窗口前 6 条同 external_id）
        if code == "coffee-foreign":
            for shadow in SHADOW_SPECS:
                published = _slot_time(shadow["day_offset"], shadow["hour"], shadow["minute"])
                slots.append(
                    {
                        "group_code": code,
                        "brand_key": brand_key,
                        "source_code": SourceCode.MICROBLOG.value,
                        "published_at": published,
                        "index": len(slots),
                        "day_offset": shadow["day_offset"],
                        "hour": shadow["hour"],
                        "forced_label": "neu",
                        "special": None,
                        "external_id": shadow["external_id"],
                    }
                )
        slots.sort(key=lambda item: (item["published_at"], item["index"]))

        pos, neu, neg = CLASS_PLAN[code]
        forced = sum(1 for item in slots if item["forced_label"])
        remaining = {"pos": pos, "neu": neu - forced, "neg": neg}
        sequence: list[str] = []
        for cls in ("pos", "neu", "neg"):
            sequence.extend([cls] * remaining[cls])
        spread = _interleave(sequence)

        cursor = 0
        neg_cursor = 0
        for item in slots:
            if item["forced_label"]:
                item["label"] = item["forced_label"]
                product = PRODUCTS[brand_key][item["index"] % 3]
                item["title"], item["body"] = _compose(code, brand_key, product, "neu", item["index"], None)
            else:
                item["label"] = spread[cursor]
                cursor += 1
                product = PRODUCTS[brand_key][item["index"] % 3]
                special = None
                if code == "coffee-foreign" and item["label"] == "neg":
                    if neg_cursor < 2:
                        special = "wire"
                    neg_cursor += 1
                item["special"] = special
                item["title"], item["body"] = _compose(
                    code, brand_key, product, item["label"], item["index"], special
                )
            if item["external_id"] is None:
                stamp = item["published_at"].strftime("%Y%m%d%H")
                item["external_id"] = f"{item['source_code']}:{code}:{stamp}:{item['index']:03d}"
            item["author"] = AUTHORS[(item["index"] * 3 + gi) % len(AUTHORS)]
            item["author_followers"] = (item["index"] * 137 + gi * 53) % 48000 + 120
            item["engagement"] = (item["index"] * 61 + gi * 29) % 4200 + 18
            item["url"] = f"https://{SOURCE_DOMAIN[item['source_code']]}/item/{item['external_id'].replace(':', '-')}"
            item["content_hash"] = content_hash(item["title"], item["body"])
            item["review_status"] = "auto"
            mentions.append(item)

    # 5 条待复核：3 条常规负面 + 2 条通报体（人读偏中性）
    pending_targets = [item for item in mentions if item["group_code"] == "coffee-foreign" and item["label"] == "neg"]
    pending_targets.sort(key=lambda item: (0 if item["special"] == "wire" else 1, item["published_at"], item["index"]))
    for item in pending_targets[:5]:
        item["review_status"] = "pending"
    return mentions


# ------------------------------------------------------- 采集窗口候选 ----


def inbox_items() -> list[dict]:
    """采集窗口原始候选：92 条，前 6 条 external_id 已在库中（去重演示）。"""
    items: list[dict] = []
    for n in range(92):
        code = GROUP_CODES[n % len(GROUP_CODES)]
        brand_key = BRAND_BY_GROUP[code]
        day_offset = -1 - (n % 7)
        hour = 5 + (n % 2)
        minute = (n * 13) % 60
        published = _slot_time(day_offset, hour, minute)
        if n % 15 == 0:
            cls = "neg"
        elif n % 5 == 0:
            cls = "neu"
        else:
            cls = "pos"
        product = PRODUCTS[brand_key][n % 3]
        special = "wire" if (cls == "neg" and n % 30 == 0) else None
        title, body = _compose(code, brand_key, product, cls, n, special)
        source = [
            SourceCode.NEWS_WIRE.value,
            SourceCode.MICROBLOG.value,
            SourceCode.VERTICAL_FORUM.value,
            SourceCode.VIDEO_AGG.value,
        ][n % 4]
        external_id = f"inbox:{n:03d}"
        items.append(
            {
                "group_code": code,
                "brand_key": brand_key,
                "source_code": source,
                "external_id": external_id,
                "title": title,
                "body": body,
                "author": AUTHORS[(n * 5) % len(AUTHORS)],
                "author_followers": (n * 311) % 26000 + 200,
                "engagement": (n * 97) % 1800 + 25,
                "url": f"https://{SOURCE_DOMAIN[source]}/item/{external_id.replace(':', '-')}",
                "published_at": published,
                "content_hash": content_hash(title, body),
                "label_hint": cls,
            }
        )
    return items


def expected_counts() -> dict[str, int]:
    pos = sum(v[0] for v in CLASS_PLAN.values())
    neu = sum(v[1] for v in CLASS_PLAN.values())
    neg = sum(v[2] for v in CLASS_PLAN.values())
    return {"pos": pos, "neu": neu, "neg": neg, "total": pos + neu + neg}


def group_class_counts() -> dict[str, dict[str, int]]:
    return {code: {"pos": v[0], "neu": v[1], "neg": v[2]} for code, v in CLASS_PLAN.items()}
