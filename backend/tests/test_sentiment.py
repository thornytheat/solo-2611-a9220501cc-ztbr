"""算法 1：中文情感打分（词典 + 程度副词 + 否定翻转 + 反问/感叹修正）。

期望值全部来自对 `analyze()` 口径的手算：
    contribution = ±weight × degree_ratio × (0.85 if negated)
    raw         = Σ contribution − 0.32 × min(rhetoric, 2)
    amplified   = raw × (1 + 0.05 × min(exclaim, 4))
    score       = round(amplified / (|amplified| + 1.85), 4)
    label       = pos if score ≥ 0.2 / neg if score ≤ −0.2 / else neu
    confidence  = round(min(1, |score| × 2.2 + min(len(hits), 4) × 0.06), 4)
"""
from __future__ import annotations

import pytest

from src.services.analysis.sentiment_analyzer import (
    ALGORITHM_VERSION,
    analyze,
    analyze_keyword_recall,
    label_for_score,
    score_distribution,
)

# --------------------------------------------------------------- 正常路径 ----


def test_positive_plain_two_hits() -> None:
    """回甘(1.1) + 回购(1.1) → raw 2.2 → 2.2 / 4.05 = 0.5432。"""
    result = analyze("回甘明显，已经回购三次了。")

    assert result.score == pytest.approx(0.5432)
    assert result.label == "pos"
    assert result.raw == pytest.approx(2.2)
    assert result.confidence == pytest.approx(1.0)
    assert result.positive_count == 2
    assert result.negative_count == 0
    assert result.negation_count == 0
    assert result.degree_count == 0
    assert [hit["word"] for hit in result.hits] == ["回甘", "回购"]
    assert [hit["offset"] for hit in result.hits] == [0, 7]
    assert [hit["contribution"] for hit in result.hits] == pytest.approx([1.1, 1.1])
    assert result.algorithm_version == ALGORITHM_VERSION


def test_negation_flips_polarity_with_damping() -> None:
    """「不」紧贴「好喝」：+1.2 → −1.2 × 0.85 = −1.02 → −1.02 / 2.87 = −0.3554。"""
    result = analyze("这个咖啡不好喝")

    assert result.score == pytest.approx(-0.3554)
    assert result.label == "neg"
    assert result.negation_count == 1
    assert result.positive_count == 1  # 记录的是词典极性，不是生效极性
    hit = result.hits[0]
    assert hit["word"] == "好喝"
    assert hit["offset"] == 5
    assert hit["polarity"] == 1
    assert hit["weight"] == pytest.approx(1.2)
    assert hit["negated"] is True
    assert hit["negator"] == "不"
    assert hit["contribution"] == pytest.approx(-1.02)
    assert result.confidence == pytest.approx(0.8419)


def test_degree_adverb_multiplies_weight() -> None:
    """「非常」(×1.45) + 满意(1.1) → raw 1.595 → 1.595 / 3.445 = 0.463。"""
    result = analyze("非常满意")

    assert result.score == pytest.approx(0.463)
    assert result.label == "pos"
    assert result.raw == pytest.approx(1.595)
    assert result.degree_count == 1
    hit = result.hits[0]
    assert hit["word"] == "满意"
    assert hit["degree"] == "非常"
    assert hit["degree_ratio"] == pytest.approx(1.45)
    assert hit["contribution"] == pytest.approx(1.595)


def test_real_seed_negative_template() -> None:
    """真实 seed 负面模板逐字：刺鼻1.2 + 异味1.3 + 异物1.5 + 失望1.3×太1.3。

    raw = −(1.2 + 1.3 + 1.5 + 1.69) = −5.69；1 个感叹号 ×1.05 → −5.9745
    score = −5.9745 / (5.9745 + 1.85) = −0.7636
    """
    text = "澄野挂耳咖啡拆开就有刺鼻异味，袋底还有异物，太失望了！"
    result = analyze(text)

    assert result.score == pytest.approx(-0.7636)
    assert result.label == "neg"
    assert result.raw == pytest.approx(-5.9745)
    assert [hit["word"] for hit in result.hits] == ["刺鼻", "异味", "异物", "失望"]
    assert result.negative_count == 4
    assert result.degree_count == 1
    assert result.exclaim_count == 1
    assert result.confidence == pytest.approx(1.0)


def test_seed_neutral_record_scores_zero() -> None:
    """真实 seed 中性模板：词典零命中 → raw 0 → score 0.0 / label neu。"""
    result = analyze("到货记录：澄野咖啡挂耳咖啡两箱，生产日期 2026-10-28，保质期 12 个月。")

    assert result.score == pytest.approx(0.0)
    assert result.raw == pytest.approx(0.0)
    assert result.label == "neu"
    assert result.hits == []
    assert result.confidence == pytest.approx(0.0)
    assert result.positive_count == 0 and result.negative_count == 0


# --------------------------------------------------------------- 边界情况 ----


def test_empty_input_is_neutral_zero() -> None:
    result = analyze("")

    assert result.score == pytest.approx(0.0)
    assert result.label == "neu"
    assert result.hits == []
    assert result.confidence == pytest.approx(0.0)
    assert (result.positive_count, result.negative_count) == (0, 0)


def test_whitespace_only_input_normalizes_to_empty() -> None:
    """全角空格 U+3000 被 NFKC 折成空格，压缩后为 ''→ 中性零分。"""
    result = analyze("  \u3000 \t\n ")

    assert result.score == pytest.approx(0.0)
    assert result.label == "neu"
    assert result.hits == []


def test_single_hit_single_char_boundary() -> None:
    """只有一个命中词：满意(1.1) → 1.1 / 2.95 = 0.3729。"""
    result = analyze("满意")

    assert result.score == pytest.approx(0.3729)
    assert len(result.hits) == 1
    assert result.hits[0]["offset"] == 0
    assert result.hits[0]["length"] == 2


def test_clause_break_stops_negation_lookback() -> None:
    """「不好喝，后来香浓」：否定不跨逗号 → −1.02 + 1.2 = 0.18 → 0.0887 neu。"""
    result = analyze("不好喝，后来香浓")

    assert result.score == pytest.approx(0.0887)
    assert result.label == "neu"
    assert result.negation_count == 1
    assert [hit["negated"] for hit in result.hits] == [True, False]
    assert [hit["word"] for hit in result.hits] == ["好喝", "香浓"]


def test_exclaim_amplification_capped_at_four() -> None:
    """6 个感叹号只放大到 ×1.2（cap=4）：1.2 × 1.2 = 1.44 → 1.44 / 3.29 = 0.4377。"""
    result = analyze("好喝！！！！！！")

    assert result.exclaim_count == 6
    assert result.raw == pytest.approx(1.44)
    assert result.score == pytest.approx(0.4377)
    assert result.label == "pos"


def test_rhetoric_penalty_capped_at_two() -> None:
    """3 个反问标记只罚 2 次（cap=2）：1.2 − 0.64 = 0.56 → 0.56 / 2.41 = 0.2324。"""
    result = analyze("难道凭什么这也叫好喝")

    assert result.rhetoric_count == 2  # 回传的是「生效次数」，不是原始命中数
    assert result.raw == pytest.approx(0.56)
    assert result.score == pytest.approx(0.2324)
    assert result.label == "pos"


def test_degree_then_negator_order_is_fixed() -> None:
    """先剥程度副词再判否定：非常满意 = +1.595（不被「非」误翻）。"""
    result = analyze("非常满意")

    assert result.hits[0]["degree"] == "非常"
    assert result.hits[0]["negator"] is None
    assert result.hits[0]["contribution"] == pytest.approx(1.595)


# ----------------------------------------------------------- 标签 / 分布 ----


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.2000, "pos"),
        (0.1999, "neu"),
        (-0.1999, "neu"),
        (-0.2000, "neg"),
        (0.0, "neu"),
        (0.9999, "pos"),
    ],
)
def test_label_thresholds_are_inclusive(score: float, expected: str) -> None:
    assert label_for_score(score) == expected


def test_score_distribution_counts_conserve_total() -> None:
    labels = ["pos", "pos", "neu", "neg", "neg", "neg"]

    dist = score_distribution(labels)

    assert dist == {"pos": 2, "neu": 1, "neg": 3, "total": 6}
    assert dist["pos"] + dist["neu"] + dist["neg"] == dist["total"]


def test_score_distribution_empty() -> None:
    assert score_distribution([]) == {"pos": 0, "neu": 0, "neg": 0, "total": 0}


# ------------------------------------------------------------- 召回匹配 ----


def test_keyword_recall_hits_keyword() -> None:
    result = analyze_keyword_recall("澄野咖啡里喝出塑料片", ["异物", "塑料"], ["澄野异物"], ["咖啡渣"])

    assert result == {
        "matched": True,
        "kept": True,
        "hit_keywords": ["塑料"],
        "hit_synonyms": [],
        "hit_excludes": [],
    }


def test_keyword_recall_synonym_matches_and_exclude_drops() -> None:
    result = analyze_keyword_recall(
        "咖啡渣很多，研磨度也粗",
        ["咖啡"],
        ["澄野咖啡"],
        ["咖啡渣"],
    )

    assert result["matched"] is True
    assert result["hit_keywords"] == ["咖啡"]
    assert result["hit_synonyms"] == []
    assert result["hit_excludes"] == ["咖啡渣"]
    assert result["kept"] is False


def test_keyword_recall_case_insensitive_and_empty() -> None:
    lower = analyze_keyword_recall("IPHONE 15 掉色", ["iPhone"], [], [])
    nothing = analyze_keyword_recall("今天天气不错", [], [], [])

    assert lower["matched"] is True and lower["hit_keywords"] == ["iPhone"]
    assert nothing == {
        "matched": False,
        "kept": False,
        "hit_keywords": [],
        "hit_synonyms": [],
        "hit_excludes": [],
    }
