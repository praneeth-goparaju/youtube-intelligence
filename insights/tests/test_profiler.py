"""Tests for the feature profiler module."""

import pytest
from insights.src.profiler import (
    compute_feature_profile,
    compute_timing_profile,
    _collect_values,
    _compute_stats,
    _bool_stats,
    _numeric_stats,
    _categorical_stats,
    _list_stats,
    _set_nested,
    _traverse,
    SKIP_FIELDS,
    MAX_CATEGORICAL_VALUES,
)


class TestBoolStats:
    def test_all_true(self):
        result = _bool_stats([True, True, True], [True, True])
        assert result == {'all': 1.0, 'top10': 1.0}

    def test_all_false(self):
        result = _bool_stats([False, False], [False])
        assert result == {'all': 0.0, 'top10': 0.0}

    def test_mixed(self):
        result = _bool_stats([True, False, True, False], [True, True])
        assert result == {'all': 0.5, 'top10': 1.0}

    def test_empty_top(self):
        result = _bool_stats([True, False], [])
        assert result == {'all': 0.5, 'top10': 0}

    def test_empty_all(self):
        result = _bool_stats([], [])
        assert result == {'all': 0, 'top10': 0}


class TestNumericStats:
    def test_basic(self):
        result = _numeric_stats([10, 20, 30], [25, 35])
        assert result == {'all_avg': 20.0, 'top10_avg': 30.0}

    def test_single_value(self):
        result = _numeric_stats([5], [10])
        assert result == {'all_avg': 5.0, 'top10_avg': 10.0}

    def test_empty_top(self):
        result = _numeric_stats([10, 20], [])
        assert result == {'all_avg': 15.0, 'top10_avg': 0}

    def test_floats(self):
        result = _numeric_stats([1.5, 2.5], [3.5])
        assert result == {'all_avg': 2.0, 'top10_avg': 3.5}


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
