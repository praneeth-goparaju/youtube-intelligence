"""Tests for the feature profiler module."""

import pytest
from insights.src.profiler import (
    compute_feature_profile,
    compute_timing_profile,
    compute_feature_correlations,
    compute_confidence,
    compute_recency_weight,
    is_significant,
    _collect_values,
    _compute_stats,
    _bool_stats,
    _numeric_stats,
    _categorical_stats,
    _list_stats,
    _set_nested,
    MAX_CATEGORICAL_VALUES,
)


class TestConfidence:
    @pytest.mark.parametrize("sample_size", [0, 5, 9])
    def test_low(self, sample_size):
        assert compute_confidence(sample_size) == "low"

    def test_medium(self):
        assert compute_confidence(10) == "medium"
        assert compute_confidence(49) == "medium"

    def test_high(self):
        assert compute_confidence(50) == "high"
        assert compute_confidence(1000) == "high"


class TestSignificance:
    def test_significant_difference(self):
        assert is_significant(0.3, 0.5) is True

    def test_not_significant(self):
        assert is_significant(0.3, 0.32) is False

    def test_exact_threshold(self):
        # Difference exactly equal to threshold (binary-exact values) is not significant
        assert is_significant(0.25, 0.5, threshold=0.25) is False

    def test_negative_direction(self):
        assert is_significant(0.5, 0.3) is True

    def test_custom_threshold(self):
        assert is_significant(0.3, 0.35, threshold=0.1) is False
        assert is_significant(0.3, 0.5, threshold=0.1) is True


class TestRecencyWeight:
    def test_recent_date(self):
        from datetime import datetime, timezone, timedelta

        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        weight = compute_recency_weight(recent)
        assert weight > 0.99

    def test_old_date(self):
        # 'Z' suffix is how YouTube/ISO timestamps usually arrive
        weight = compute_recency_weight("2020-01-01T00:00:00Z")
        assert 0.0 < weight < 0.5

    def test_one_half_life(self):
        from datetime import datetime, timezone, timedelta

        one_year_ago = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        weight = compute_recency_weight(one_year_ago, half_life_days=365)
        assert abs(weight - 0.5) < 0.05

    def test_invalid_date(self):
        weight = compute_recency_weight("not-a-date")
        assert weight == 1.0

    def test_unsupported_type(self):
        # Neither a string nor a datetime: no decay
        weight = compute_recency_weight(12345)
        assert weight == 1.0

    def test_aware_datetime(self):
        # Firestore returns publishedAt as a (tz-aware) datetime, not a string
        from datetime import datetime, timezone, timedelta

        one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
        assert compute_recency_weight(one_year_ago) == pytest.approx(0.5, abs=0.001)

    def test_naive_datetime_treated_as_utc(self):
        from datetime import datetime, timezone, timedelta

        two_years_ago = (datetime.now(timezone.utc) - timedelta(days=730)).replace(tzinfo=None)
        assert compute_recency_weight(two_years_ago) == pytest.approx(0.25, abs=0.001)

    def test_firestore_datetime_with_nanoseconds(self):
        from datetime import datetime, timezone, timedelta

        DatetimeWithNanoseconds = pytest.importorskip("google.api_core.datetime_helpers").DatetimeWithNanoseconds
        ts = datetime.now(timezone.utc) - timedelta(days=365)
        published = DatetimeWithNanoseconds(
            ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second, tzinfo=timezone.utc
        )
        assert compute_recency_weight(published) == pytest.approx(0.5, abs=0.001)


class TestSignificanceWithGroupSizes:
    def test_small_top_group_never_significant(self):
        # Large gap, but only 5 top videos (< MIN_TOP_FOR_SIGNIFICANCE)
        assert is_significant(0.2, 0.8, n_top=5, n_all=500) is False

    def test_z_test_passes(self):
        # se = sqrt(0.2*0.8/50 * 450/499) ~= 0.0537; |0.4-0.2|/se ~= 3.7
        assert is_significant(0.2, 0.4, n_top=50, n_all=500) is True

    def test_z_test_fails(self):
        # Same gap with 10 top videos: se ~= 0.12, z ~= 1.66 < 1.96
        assert is_significant(0.2, 0.4, n_top=10, n_all=100) is False

    def test_bool_stats_use_group_sizes(self):
        all_vals = [True] * 20 + [False] * 80
        # 10 top videos, 7 True: rate 0.7 vs 0.2 -> z ~= 3.7
        top_vals = [True] * 7 + [False] * 3
        assert _bool_stats(all_vals, top_vals) == {
            "all": 0.2,
            "top10": 0.7,
            "confidence": "medium",  # min(100, 10) = 10
            "significant": True,
        }
        # Same rates with 2 top videos: too few for significance, low confidence
        assert _bool_stats(all_vals, [True, False])["confidence"] == "low"
        assert _bool_stats(all_vals, [True, True])["significant"] is False


class TestBoolStats:
    def test_empty_top(self):
        result = _bool_stats([True, False], [])
        assert result["all"] == 0.5
        assert result["top10"] == 0


class TestNumericStats:
    def test_empty_top(self):
        result = _numeric_stats([10, 20], [])
        assert result["all_avg"] == 15.0
        assert result["top10_avg"] == 0

    def test_confidence_limited_by_top_group(self):
        result = _numeric_stats(list(range(200)), [1, 2, 3])
        assert result["confidence"] == "low"


class TestCategoricalStats:
    def test_too_many_unique_values(self):
        values = [f"value_{i}" for i in range(MAX_CATEGORICAL_VALUES + 1)]
        result = _categorical_stats(values, [])
        assert result is None

    def test_within_limit(self):
        values = [f"value_{i}" for i in range(MAX_CATEGORICAL_VALUES)]
        result = _categorical_stats(values, values[:5])
        assert result is not None

    def test_empty_top(self):
        result = _categorical_stats(["a", "b"], [])
        assert result is not None
        assert result["top10"] == {}


class TestListStats:
    def test_string_items(self):
        all_vals = [["a", "b"], ["a", "c"], ["a"]]
        top_vals = [["a", "b"]]
        result = _list_stats(all_vals, top_vals)
        # Rates are per video (3 all, 1 top), not per item
        assert result["topItems"] == {
            "a": {"all": 1.0, "top10": 1.0},
            "b": {"all": 0.333, "top10": 1.0},
            "c": {"all": 0.333, "top10": 0.0},
        }


class TestComputeStats:
    def test_bool_detection(self):
        result = _compute_stats([True, False], [True])
        assert "all" in result
        assert "top10" in result

    def test_none_values_filtered(self):
        result = _compute_stats([None, None], [None])
        assert result is None


class TestMixedListAndStringValues:
    """Legacy `title` stores word lists as lists; title_description as comma-separated strings."""

    _EXPECTED = {
        "all_avg_count": 1.5,
        "top10_avg_count": 2.0,
        "confidence": "low",
        "topItems": {
            "best": {"all": 0.5, "top10": 1.0},
            "easy": {"all": 0.5, "top10": 0.0},
            "secret": {"all": 0.5, "top10": 1.0},
        },
    }

    def test_list_first(self):
        legacy = {"hooks": {"powerWords": ["easy"]}}
        new = {"hooks": {"powerWords": "best, secret"}}
        profile = compute_feature_profile([legacy, new], [new])
        assert profile["hooks"]["powerWords"] == self._EXPECTED

    def test_string_first(self):
        legacy = {"hooks": {"powerWords": ["easy"]}}
        new = {"hooks": {"powerWords": "best, secret"}}
        profile = compute_feature_profile([new, legacy], [new])
        assert profile["hooks"]["powerWords"] == self._EXPECTED


class TestWeightsApplyToAllStatTypes:
    def test_bool_categorical_and_list_are_weighted(self):
        all_analyses = [
            {"flag": True, "mood": "happy", "tags": ["a"]},
            {"flag": False, "mood": "sad", "tags": []},
        ]
        profile = compute_feature_profile(all_analyses, [all_analyses[0]], all_weights=[0.25, 0.75], top_weights=[1.0])
        assert profile["flag"]["all"] == 0.25
        assert profile["mood"]["all"] == {"happy": 0.25, "sad": 0.75}
        assert profile["tags"]["all_avg_count"] == 0.25
        assert profile["tags"]["topItems"] == {"a": {"all": 0.25, "top10": 1.0}}


class TestSetNested:
    def test_path_conflict(self):
        d = {"a": "not_a_dict"}
        _set_nested(d, "a.b", 2)
        # Should skip silently due to path conflict
        assert d == {"a": "not_a_dict"}


class TestCollectValues:
    def test_skip_fields(self):
        analyses = [{"analyzedAt": "2024-01-01", "score": 5}]
        result = _collect_values(analyses)
        assert "analyzedAt" not in result
        assert "score" in result

    def test_analyzer_metadata_skipped(self):
        # Metadata written by the sync analyzers and the batch importer is not a feature
        analyses = [
            {
                "analyzedAt": "2026-01-01T00:00:00",
                "modelUsed": "gemini-2.5-flash",
                "analysisVersion": "2.0",
                "rawTitle": "Biryani",
                "hasDescription": True,
                "batchMode": True,
                "score": 5,
            }
        ]
        assert dict(_collect_values(analyses)) == {"score": [5]}

    def test_list_values(self):
        analyses = [{"tags": ["a", "b"]}, {"tags": ["c"]}]
        result = _collect_values(analyses)
        assert result["tags"] == [["a", "b"], ["c"]]

    def test_list_of_dicts_skipped(self):
        # Legacy structure.segments is a list of objects: no meaningful leaf stats
        analyses = [{"structure": {"segments": [{"text": "a"}], "patternType": "single"}}]
        result = _collect_values(analyses)
        assert dict(result) == {"structure.patternType": ["single"]}


_PROFILE_ALL = [
    {"hasFace": True, "isHD": True, "score": 10, "mood": "happy", "tags": ["a", "b"], "colors": {"bright": True}},
    {"hasFace": False, "isHD": True, "score": 20, "mood": "sad", "tags": ["a"], "colors": {"bright": False}},
    {"hasFace": True, "isHD": True, "score": 30, "mood": "happy", "tags": ["a", "c"], "colors": {"bright": False}},
    {"hasFace": False, "isHD": True, "score": 40, "mood": "happy", "tags": [], "colors": {"bright": False}},
]
_PROFILE_TOP = [_PROFILE_ALL[2]]


class TestComputeFeatureProfile:
    @pytest.mark.parametrize(
        "path, expected",
        [
            # n_top=1 < MIN_TOP_FOR_SIGNIFICANCE, so large rate gaps are not flagged significant
            ("hasFace", {"all": 0.5, "top10": 1.0, "confidence": "low", "significant": False}),
            ("isHD", {"all": 1.0, "top10": 1.0, "confidence": "low", "significant": False}),
            ("score", {"all_avg": 25.0, "top10_avg": 30.0, "confidence": "low"}),
            ("mood", {"all": {"happy": 0.75, "sad": 0.25}, "top10": {"happy": 1.0}, "confidence": "low"}),
            (
                "tags",
                {
                    "all_avg_count": 1.25,
                    "top10_avg_count": 2.0,
                    "confidence": "low",
                    "topItems": {
                        "a": {"all": 0.75, "top10": 1.0},
                        "b": {"all": 0.25, "top10": 0.0},
                        "c": {"all": 0.25, "top10": 1.0},
                    },
                },
            ),
            ("colors.bright", {"all": 0.25, "top10": 0.0, "confidence": "low", "significant": False}),
        ],
        ids=["bool", "bool-not-significant", "numeric", "categorical", "list", "nested"],
    )
    def test_feature_stats(self, path, expected):
        profile = compute_feature_profile(_PROFILE_ALL, _PROFILE_TOP)

        node = profile
        for key in path.split("."):
            node = node[key]
        assert node == expected

    def test_empty_analyses(self):
        profile = compute_feature_profile([], [])
        assert profile == {}

    def test_with_weights(self):
        all_analyses = [{"score": 10}, {"score": 20}, {"score": 30}]
        top_analyses = [{"score": 25}]
        profile = compute_feature_profile(
            all_analyses,
            top_analyses,
            all_weights=[0.1, 0.1, 0.8],
            top_weights=[1.0],
        )
        # Weighted avg of [10, 20, 30] with [0.1, 0.1, 0.8] = 1 + 2 + 24 = 27.0
        assert profile["score"] == {"all_avg": 27.0, "top10_avg": 25.0, "confidence": "low"}


def _timed_video(day, hour, vps):
    return {"video": {"calculated": {"publishDayOfWeek": day, "publishHourIST": hour}}, "vps": vps}


class TestComputeTimingProfile:
    def test_basic_timing(self):
        videos = [_timed_video("Monday", 10, vps) for vps in [1.0, 1.0, 1.0, 1.0, 2.0]]
        videos += [_timed_video("Friday", 18, vps) for vps in [2.0, 3.0, 4.0, 3.0, 3.0]]

        result = compute_timing_profile(videos, lambda v: v["vps"])

        assert result["bestDays"] == [
            {"day": "Friday", "avgViewsPerSubscriber": 3.0, "videoCount": 5},
            {"day": "Monday", "avgViewsPerSubscriber": 1.2, "videoCount": 5},
        ]
        assert result["bestHours"] == [
            {"hour": 18, "avgViewsPerSubscriber": 3.0, "videoCount": 5},
            {"hour": 10, "avgViewsPerSubscriber": 1.2, "videoCount": 5},
        ]

    def test_insufficient_data(self):
        videos = [
            {"video": {"calculated": {"publishDayOfWeek": "Monday", "publishHourIST": 10}}},
        ]

        def get_vps(v):
            return 1.0

        result = compute_timing_profile(videos, get_vps)
        # Less than 5 videos per day/hour, so nothing qualifies
        assert result["bestDays"] == []
        assert result["bestHours"] == []

    def test_zero_vps_excluded(self):
        videos = [
            {"video": {"calculated": {"publishDayOfWeek": "Monday", "publishHourIST": 10}}},
        ] * 10

        def get_vps(v):
            return 0  # All zero

        result = compute_timing_profile(videos, get_vps)
        assert result["bestDays"] == []


class TestFeatureCorrelations:
    def test_basic_pairwise(self):
        # Create analyses where hasFace and isBright co-occur more in top
        all_analyses = [
            {"hasFace": True, "isBright": True},
            {"hasFace": True, "isBright": False},
            {"hasFace": False, "isBright": True},
            {"hasFace": False, "isBright": False},
        ] * 10  # 40 total

        top_analyses = [
            {"hasFace": True, "isBright": True},
        ] * 10  # All top have both True

        result = compute_feature_correlations(all_analyses, top_analyses)
        # Both true in 10/40 of all vs 10/10 of top -> lift 1.0 / 0.25
        assert result == [{"pair": ["hasFace", "isBright"], "coOccurrence": {"all": 0.25, "top10": 1.0}, "lift": 4.0}]

    def test_insufficient_data(self):
        all_analyses = [{"a": True}] * 5  # Too few
        top_analyses = [{"a": True}]
        result = compute_feature_correlations(all_analyses, top_analyses)
        assert result == []

    def test_single_feature_returns_empty(self):
        all_analyses = [{"a": True, "b": "not_bool"}] * 20
        top_analyses = [{"a": True, "b": "not_bool"}] * 5
        result = compute_feature_correlations(all_analyses, top_analyses)
        # Only one boolean feature, can't compute pairs
        assert result == []
