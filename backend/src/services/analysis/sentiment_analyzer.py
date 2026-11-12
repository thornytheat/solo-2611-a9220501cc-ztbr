"""中文情感打分（算法 1，纯函数、无随机、可复现）。

口径：
1. 归一化（NFKC + 空白压缩，`src.utils.textutils.normalize`）后做最长匹配；
2. 每个命中词贡献 = 极性 × 词典权重 × 程度副词倍率（否定则极性翻转并乘阻尼）；
3. 反问标记额外负向惩罚；感叹号做幅度放大（最多 4 个）；
4. `score = raw / (|raw| + 1.85)` ∈ (-1, 1)，阈值 ±0.20 划分 pos / neu / neg。

同输入必然同分：所有系数来自 settings，无时间、无随机、无浮点累积顺序差异。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src.config.settings import settings
from src.services.analysis.lexicon import (
    DEGREE_ADVERBS,
    NEGATIVE_LEXICON,
    NEGATORS,
    POSITIVE_LEXICON,
    RHETORICAL_MARKERS,
    polarity_index,
)
from src.utils.textutils import fold

ALGORITHM_VERSION = "sent-1.0.0"

_INDEX = polarity_index()
# 最长匹配优先：按长度倒序，同长度按字典序保证稳定
_TERMS: tuple[str, ...] = tuple(sorted(_INDEX.keys(), key=lambda w: (-len(w), w)))
_DEGREES: tuple[str, ...] = tuple(sorted(DEGREE_ADVERBS.keys(), key=lambda w: (-len(w), w)))
_NEGATORS: tuple[str, ...] = tuple(sorted(NEGATORS, key=lambda w: (-len(w), w)))
_MAX_TERM = max(len(w) for w in _TERMS)
_CLAUSE_BREAKS = ("。", "！", "？", "；", "\n", "，", "、", ":", "：", "!", "?", ";", ",")


@dataclass
class Hit:
    word: str
    offset: int
    length: int
    polarity: int
    weight: float
    degree: str | None = None
    degree_ratio: float = 1.0
    negated: bool = False
    negator: str | None = None
    contribution: float = 0.0
    role: str = "polarity_word"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SentimentResult:
    score: float
    label: str
    confidence: float
    raw: float
    hits: list[dict] = field(default_factory=list)
    positive_count: int = 0
    negative_count: int = 0
    negation_count: int = 0
    degree_count: int = 0
    rhetoric_count: int = 0
    exclaim_count: int = 0
    algorithm_version: str = ALGORITHM_VERSION

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "label": self.label,
            "confidence": self.confidence,
            "raw": self.raw,
            "hits": self.hits,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "negation_count": self.negation_count,
            "degree_count": self.degree_count,
            "rhetoric_count": self.rhetoric_count,
            "exclaim_count": self.exclaim_count,
            "algorithm_version": self.algorithm_version,
        }


def _lookback_degree(window: str) -> tuple[str | None, str]:
    for degree in _DEGREES:
        if window.endswith(degree):
            return degree, window[: -len(degree)]
    return None, window


def _lookback_negator(window: str) -> str | None:
    for negator in _NEGATORS:
        if window.endswith(negator):
            return negator
    return None


def label_for_score(score: float) -> str:
    if score >= settings.sentiment_pos_threshold:
        return "pos"
    if score <= settings.sentiment_neg_threshold:
        return "neg"
    return "neu"


def analyze(raw_text: str) -> SentimentResult:
    """对一段文本打分。文本会先归一化，偏移量对应归一化后的文本。"""
    text = fold(raw_text)
    hits: list[Hit] = []
    raw = 0.0
    i = 0
    n = len(text)
    while i < n:
        matched = None
        for term in _TERMS:
            if len(term) > _MAX_TERM:
                continue
            if text.startswith(term, i):
                matched = term
                break
        if matched is None:
            i += 1
            continue

        weight, polarity = _INDEX[matched]
        window_start = max(0, i - settings.degree_lookback)
        window = text[window_start:i]
        # 不跨分句回看（「…不好喝，后来香浓」不应把否定带过来）
        for breaker in _CLAUSE_BREAKS:
            pos = window.rfind(breaker)
            if pos >= 0:
                window = window[pos + 1 :]

        degree, rest = _lookback_degree(window)
        negator = _lookback_negator(rest) if rest else None
        degree_ratio = DEGREE_ADVERBS.get(degree, 1.0) if degree else 1.0
        negated = negator is not None
        effective_polarity = polarity * (-1 if negated else 1)
        contribution = effective_polarity * weight * degree_ratio
        if negated:
            contribution *= settings.negation_damping

        hit = Hit(
            word=matched,
            offset=i,
            length=len(matched),
            polarity=polarity,
            weight=weight,
            degree=degree,
            degree_ratio=round(degree_ratio, 4),
            negated=negated,
            negator=negator,
            contribution=round(contribution, 4),
        )
        hits.append(hit)
        raw += contribution
        i += len(matched)

    exclaim_count = raw_text.count("！") + raw_text.count("!")
    rhetoric_count = 0
    for marker in RHETORICAL_MARKERS:
        rhetoric_count += text.count(marker)
    rhetoric_applied = min(rhetoric_count, settings.rhetoric_cap)
    raw -= settings.rhetoric_penalty * rhetoric_applied
    amplification = 1 + settings.exclaim_step * min(exclaim_count, settings.exclaim_cap)
    amplified = raw * amplification
    denominator = abs(amplified) + settings.sentiment_normalizer
    score = round(amplified / denominator, 4) if denominator else 0.0

    positive_count = sum(1 for h in hits if h.polarity > 0)
    negative_count = sum(1 for h in hits if h.polarity < 0)
    negation_count = sum(1 for h in hits if h.negated)
    degree_count = sum(1 for h in hits if h.degree)
    confidence = round(min(1.0, abs(score) * 2.2 + min(len(hits), 4) * 0.06), 4)

    return SentimentResult(
        score=score,
        label=label_for_score(score),
        confidence=confidence,
        raw=round(amplified, 4),
        hits=[h.to_dict() for h in hits],
        positive_count=positive_count,
        negative_count=negative_count,
        negation_count=negation_count,
        degree_count=degree_count,
        rhetoric_count=rhetoric_applied,
        exclaim_count=exclaim_count,
    )


def score_distribution(labels: list[str]) -> dict[str, int]:
    return {
        "pos": sum(1 for item in labels if item == "pos"),
        "neu": sum(1 for item in labels if item == "neu"),
        "neg": sum(1 for item in labels if item == "neg"),
        "total": len(labels),
    }


def analyze_keyword_recall(text: str, keywords: list[str], synonyms: list[str], excludes: list[str]) -> dict:
    """召回试算：主关键词 ∪ 同义词，命中任一即召回；排除词命中则剔除。

    返回命中的关键词与排除词（用于「试算召回预览」展示口径）。
    """
    folded = fold(text)
    hit_keywords: list[str] = []
    for word in keywords:
        if word and word.lower() in folded:
            hit_keywords.append(word)
    hit_synonyms: list[str] = []
    for word in synonyms:
        if word and word.lower() in folded:
            hit_synonyms.append(word)
    hit_excludes: list[str] = []
    for word in excludes:
        if word and word.lower() in folded:
            hit_excludes.append(word)
    matched = bool(hit_keywords or hit_synonyms)
    kept = matched and not hit_excludes
    return {
        "matched": matched,
        "kept": kept,
        "hit_keywords": hit_keywords,
        "hit_synonyms": hit_synonyms,
        "hit_excludes": hit_excludes,
    }
