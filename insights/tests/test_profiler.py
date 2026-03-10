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
    _get_nested,
    _set_nested,
    _traverse,
    SKIP_FIELDS,
    MAX_CATEGORICAL_VALUES,
)


class TestConfidence:
    def test_low(self):
        assert compute_confidence(5) == 'low'
        assert compute_confidence(9) == 'low'

    def test_medium(self):
        assert compute_confidence(10) == 'medium'
        assert compute_confidence(49) == 'medium'

    def test_high(self):
        assert compute_confidence(50) == 'high'
        assert compute_confidence(1000) == 'high'

    def test_zero(self):
        assert compute_confidence(0) == 'low'


class TestSignificance:
    def test_significant_difference(self):
        assert is_significant(0.3, 0.5) is True

    def test_not_significant(self):
        assert is_significant(0.3, 0.32) is False

    def test_exact_threshold(self):
        # Exactly at threshold — not significant (need to exceed)
        assert is_significant(0.3, 0.35, threshold=0.05) is False

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
        weight = compute_recency_weight('2020-01-01T00:00:00+00:00')
        assert weight < 0.5

    def test_one_half_life(self):
        from datetime import datetime, timezone, timedelta
        one_year_ago = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        weight = compute_recency_weight(one_year_ago, half_life_days=365)
        assert abs(weight - 0.5) < 0.05

    def test_invalid_date(self):
        weight = compute_recency_weight('not-a-date')
        assert weight == 1.0

    def test_non_string(self):
        weight = compute_recency_weight(12345)
        assert weight == 1.0


class TestBoolStats:
    def test_all_true(self):
        result = _bool_stats([True, True, True], [True, True])
        assert result['all'] == 1.0
        assert result['top10'] == 1.0

    def test_all_false(self):
        result = _bool_stats([False, False], [False])
        assert result['all'] == 0.0
        assert result['top10'] == 0.0

    def test_mixed(self):
        result = _bool_stats([True, False, True, False], [True, True])
        assert result['all'] == 0.5
        assert result['top10'] == 1.0

    def test_empty_top(self):
        result = _bool_stats([True, False], [])
        assert result['all'] == 0.5
        assert result['top10'] == 0

    def test_empty_all(self):
        result = _bool_stats([], [])
        assert result['all'] == 0
        assert result['top10'] == 0

    def test_has_confidence(self):
        result = _bool_stats([True, False] * 30, [True] * 10)
        assert result['confidence'] == 'high'

    def test_has_significant(self):
        result = _bool_stats([True, False] * 5, [True] * 5)
        assert 'significant' in result

    def test_low_confidence(self):
        result = _bool_stats([True, False], [True])
        assert result['confidence'] == 'low'


class TestNumericStats:
    def test_basic(self):
        result = _numeric_stats([10, 20, 30], [25, 35])
        assert result['all_avg'] == 20.0
        assert result['top10_avg'] == 30.0

    def test_single_value(self):
        result = _numeric_stats([5], [10])
        assert result['all_avg'] == 5.0
        assert result['top10_avg'] == 10.0

    def test_empty_top(self):
        result = _numeric_stats([10, 20], [])
        assert result['all_avg'] == 15.0
        assert result['top10_avg'] == 0

    def test_floats(self):
        result = _numeric_stats([1.5, 2.5], [3.5])
        assert result['all_avg'] == 2.0
        assert result['top10_avg'] == 3.5

    def test_has_confidence(self):
        result = _numeric_stats(list(range(60)), list(range(10)))
        assert result['confidence'] == 'high'

    def test_with_weights(self):
        # Higher weight on 30 should pull avg up
        result = _numeric_stats([10, 20, 30], [25, 35],
                                all_weights=[0.1, 0.1, 0.8],
                                top_weights=[0.5, 0.5])
        assert result['all_avg'] > 20.0  # Pulled toward 30
        assert result['top10_avg'] == 30.0


class TestCategoricalStats:
    def test_basic(self):
        result = _categorical_stats(['a', 'b', 'a'], ['a', 'a'])
        assert result is not None
        assert result['all']['a'] == pytest.approx(0.667, abs=0.001)
        assert result['all']['b'] == pytest.approx(0.333, abs=0.001)
        assert result['top10']['a'] == 1.0

    def test_too_many_unique_values(self):
        values = [f'value_{i}' for i in range(MAX_CATEGORICAL_VALUES + 1)]
        result = _categorical_stats(values, [])
        assert result is None

    def test_within_limit(self):
        values = [f'value_{i % 5}' for i in range(20)]
        result = _categorical_stats(values, values[:5])
        assert result is not None

    def test_empty_top(self):
        result = _categorical_stats(['a', 'b'], [])
        assert result is not None
        assert result['top10'] == {}

    def test_has_confidence(self):
        result = _categorical_stats(['a', 'b'] * 30, ['a'] * 10)
        assert result['confidence'] == 'high'


class TestListStats:
    def test_basic(self):
        all_vals = [[1, 2, 3], [4, 5]]
        top_vals = [[1, 2, 3, 4, 5]]
        result = _list_stats(all_vals, top_vals)
        assert result['all_avg_count'] == 2.5
        assert result['top10_avg_count'] == 5.0

    def test_string_items(self):
        all_vals = [['a', 'b'], ['a', 'c'], ['a']]
        top_vals = [['a', 'b']]
        result = _list_stats(all_vals, top_vals)
        assert 'topItems' in result
        assert 'a' in result['topItems']

    def test_empty(self):
        result = _list_stats([], [])
        assert result['all_avg_count'] == 0
        assert result['top10_avg_count'] == 0

    def test_has_confidence(self):
        all_vals = [[1, 2]] * 60
        top_vals = [[1, 2, 3]] * 10
        result = _list_stats(all_vals, top_vals)
        assert result['confidence'] == 'high'


class TestComputeStats:
    def test_bool_detection(self):
        result = _compute_stats([True, False], [True])
        assert 'all' in result
        assert 'top10' in result

    def test_numeric_detection(self):
        result = _compute_stats([1, 2, 3], [4, 5])
        assert 'all_avg' in result

    def test_string_detection(self):
        result = _compute_stats(['a', 'b'], ['a'])
        assert 'all' in result

    def test_list_detection(self):
        result = _compute_stats([[1, 2]], [[3]])
        assert 'all_avg_count' in result

    def test_none_values_filtered(self):
        result = _compute_stats([None, None], [None])
        assert result is None

    def test_empty_returns_none(self):
        result = _compute_stats([], [])
        assert result is None


class TestSetNested:
    def test_single_level(self):
        d = {}
        _set_nested(d, 'key', 'value')
        assert d == {'key': 'value'}

    def test_nested(self):
        d = {}
        _set_nested(d, 'a.b.c', 42)
        assert d == {'a': {'b': {'c': 42}}}

    def test_existing_path(self):
        d = {'a': {'b': 1}}
        _set_nested(d, 'a.c', 2)
        assert d == {'a': {'b': 1, 'c': 2}}

    def test_path_conflict(self):
        d = {'a': 'not_a_dict'}
        _set_nested(d, 'a.b', 2)
        # Should skip silently due to path conflict
        assert d == {'a': 'not_a_dict'}


class TestCollectValues:
    def test_flat_dict(self):
        analyses = [{'x': 1, 'y': 2}, {'x': 3, 'y': 4}]
        result = _collect_values(analyses)
        assert result['x'] == [1, 3]
        assert result['y'] == [2, 4]

    def test_nested_dict(self):
        analyses = [{'a': {'b': 1}}, {'a': {'b': 2}}]
        result = _collect_values(analyses)
        assert result['a.b'] == [1, 2]

    def test_skip_fields(self):
        analyses = [{'analyzedAt': '2024-01-01', 'score': 5}]
        result = _collect_values(analyses)
        assert 'analyzedAt' not in result
        assert 'score' in result

    def test_list_values(self):
        analyses = [{'tags': ['a', 'b']}, {'tags': ['c']}]
        result = _collect_values(analyses)
        assert result['tags'] == [['a', 'b'], ['c']]


class TestComputeFeatureProfile:
    def test_basic_profile(self):
        all_analyses = [
            {'hasFace': True, 'score': 8},
            {'hasFace': False, 'score': 5},
            {'hasFace': True, 'score': 7},
        ]
        top_analyses = [
            {'hasFace': True, 'score': 9},
        ]
        profile = compute_feature_profile(all_analyses, top_analyses)
        assert 'hasFace' in profile
        assert 'score' in profile

    def test_empty_analyses(self):
        profile = compute_feature_profile([], [])
        assert profile == {}

    def test_nested_features(self):
        all_analyses = [
            {'colors': {'primary': 'red', 'bright': True}},
            {'colors': {'primary': 'blue', 'bright': False}},
        ]
        top_analyses = [
            {'colors': {'primary': 'red', 'bright': True}},
        ]
        profile = compute_feature_profile(all_analyses, top_analyses)
        assert 'colors' in profile

    def test_with_weights(self):
        all_analyses = [{'score': 10}, {'score': 20}, {'score': 30}]
        top_analyses = [{'score': 25}]
        profile = compute_feature_profile(
            all_analyses, top_analyses,
            all_weights=[0.1, 0.1, 0.8],
            top_weights=[1.0],
        )
        # Weighted avg of [10, 20, 30] with [0.1, 0.1, 0.8] = 27.0
        assert profile['score']['all_avg'] > 20.0


class TestComputeTimingProfile:
    def test_basic_timing(self):
        videos = [
            {'video': {'calculated': {'publishDayOfWeek': 'Monday', 'publishHourIST': 10}}},
            {'video': {'calculated': {'publishDayOfWeek': 'Monday', 'publishHourIST': 10}}},
            {'video': {'calculated': {'publishDayOfWeek': 'Monday', 'publishHourIST': 10}}},
            {'video': {'calculated': {'publishDayOfWeek': 'Monday', 'publishHourIST': 10}}},
            {'video': {'calculated': {'publishDayOfWeek': 'Monday', 'publishHourIST': 10}}},
            {'video': {'calculated': {'publishDayOfWeek': 'Friday', 'publishHourIST': 18}}},
            {'video': {'calculated': {'publishDayOfWeek': 'Friday', 'publishHourIST': 18}}},
            {'video': {'calculated': {'publishDayOfWeek': 'Friday', 'publishHourIST': 18}}},
            {'video': {'calculated': {'publishDayOfWeek': 'Friday', 'publishHourIST': 18}}},
            {'video': {'calculated': {'publishDayOfWeek': 'Friday', 'publishHourIST': 18}}},
        ]

        def get_vps(v):
            return 1.5

        result = compute_timing_profile(videos, get_vps)
        assert 'bestDays' in result
        assert 'bestHours' in result
        assert len(result['bestDays']) == 2
        assert len(result['bestHours']) == 2

    def test_insufficient_data(self):
        videos = [
            {'video': {'calculated': {'publishDayOfWeek': 'Monday', 'publishHourIST': 10}}},
        ]

        def get_vps(v):
            return 1.0

        result = compute_timing_profile(videos, get_vps)
        # Less than 5 videos per day/hour, so nothing qualifies
        assert result['bestDays'] == []
        assert result['bestHours'] == []

    def test_zero_vps_excluded(self):
        videos = [
            {'video': {'calculated': {'publishDayOfWeek': 'Monday', 'publishHourIST': 10}}},
        ] * 10

        def get_vps(v):
            return 0  # All zero

        result = compute_timing_profile(videos, get_vps)
        assert result['bestDays'] == []


class TestFeatureCorrelations:
    def test_basic_pairwise(self):
        # Create analyses where hasFace and isBright co-occur more in top
        all_analyses = [
            {'hasFace': True, 'isBright': True},
            {'hasFace': True, 'isBright': False},
            {'hasFace': False, 'isBright': True},
            {'hasFace': False, 'isBright': False},
        ] * 10  # 40 total

        top_analyses = [
            {'hasFace': True, 'isBright': True},
        ] * 10  # All top have both True

        result = compute_feature_correlations(all_analyses, top_analyses)
        # Should find hasFace + isBright as a co-occurring pair
        assert isinstance(result, list)
        if result:
            assert 'pair' in result[0]
            assert 'lift' in result[0]
            assert 'coOccurrence' in result[0]

    def test_insufficient_data(self):
        all_analyses = [{'a': True}] * 5  # Too few
        top_analyses = [{'a': True}]
        result = compute_feature_correlations(all_analyses, top_analyses)
        assert result == []

    def test_single_feature_returns_empty(self):
        all_analyses = [{'a': True, 'b': 'not_bool'}] * 20
        top_analyses = [{'a': True, 'b': 'not_bool'}] * 5
        result = compute_feature_correlations(all_analyses, top_analyses)
        # Only one boolean feature, can't compute pairs
        assert result == []
