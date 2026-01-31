"""Tests for insights main module helper functions."""

import pytest
from insights.src.main import (
    get_views_per_subscriber,
    get_content_type,
    group_by_content_type,
    split_top_performers,
)


class TestGetViewsPerSubscriber:
    def test_from_calculated(self):
        video_data = {
            'video': {'calculated': {'viewsPerSubscriber': 2.5}},
        }
        assert get_views_per_subscriber(video_data) == 2.5

    def test_computed_from_views_and_subs(self):
        video_data = {
            'video': {'viewCount': 1000, 'calculated': {}},
            'channel': {'subscriberCount': 500},
        }
        assert get_views_per_subscriber(video_data) == 2.0

    def test_zero_subscribers(self):
        video_data = {
            'video': {'viewCount': 1000, 'calculated': {}},
            'channel': {'subscriberCount': 0},
        }
        assert get_views_per_subscriber(video_data) == 0.0

    def test_missing_data(self):
        video_data = {}
        assert get_views_per_subscriber(video_data) == 0.0

    def test_none_vps(self):
        video_data = {
            'video': {'viewCount': 500, 'calculated': {'viewsPerSubscriber': None}},
            'channel': {'subscriberCount': 100},
        }
        assert get_views_per_subscriber(video_data) == 5.0


class TestGetContentType:
    def test_basic(self):
        video_data = {
            'title_analysis': {
                'contentSignals': {'contentType': 'recipe'}
            }
        }
        assert get_content_type(video_data) == 'recipe'

    def test_missing_analysis(self):
        assert get_content_type({}) == 'unknown'

    def test_missing_content_type(self):
        video_data = {'title_analysis': {'contentSignals': {}}}
        assert get_content_type(video_data) == 'unknown'


class TestGroupByContentType:
    def test_basic_grouping(self):
        videos = [
            {'title_analysis': {'contentSignals': {'contentType': 'recipe'}}},
            {'title_analysis': {'contentSignals': {'contentType': 'recipe'}}},
            {'title_analysis': {'contentSignals': {'contentType': 'vlog'}}},
        ]
        groups = group_by_content_type(videos)
        assert len(groups['recipe']) == 2
        assert len(groups['vlog']) == 1

    def test_empty_list(self):
        groups = group_by_content_type([])
        assert groups == {}


class TestSplitTopPerformers:
    def test_basic_split(self):
        videos = []
        for vps in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]:
            videos.append({
                'video': {'calculated': {'viewsPerSubscriber': vps}},
            })

        all_vids, top_vids, threshold = split_top_performers(videos)
        assert len(all_vids) == 10
        # Top 10% of 10 videos = 1 video (vps >= 90th percentile)
        assert len(top_vids) >= 1
        assert threshold > 0

    def test_empty_videos(self):
        all_vids, top_vids, threshold = split_top_performers([])
        assert all_vids == []
        assert top_vids == []
        assert threshold == 0.0

    def test_all_same_vps(self):
        videos = [
            {'video': {'calculated': {'viewsPerSubscriber': 5.0}}}
            for _ in range(10)
        ]
        all_vids, top_vids, threshold = split_top_performers(videos)
        assert len(all_vids) == 10
        # All have same vps, so all should be >= threshold
        assert len(top_vids) == 10
