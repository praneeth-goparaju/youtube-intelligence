"""Tests for insights main module helper functions."""

from insights.src.main import (
    get_views_per_subscriber,
    get_engagement_rate,
    get_content_type,
    group_by_content_type,
    split_top_performers,
    remove_outliers,
    _extract_description_analysis,
)


class TestGetViewsPerSubscriber:
    def test_from_calculated(self):
        video_data = {
            "video": {"calculated": {"viewsPerSubscriber": 2.5}},
        }
        assert get_views_per_subscriber(video_data) == 2.5

    def test_computed_from_views_and_subs(self):
        video_data = {
            "video": {"viewCount": 1000, "calculated": {}},
            "channel": {"subscriberCount": 500},
        }
        assert get_views_per_subscriber(video_data) == 2.0

    def test_zero_subscribers(self):
        video_data = {
            "video": {"viewCount": 1000, "calculated": {}},
            "channel": {"subscriberCount": 0},
        }
        assert get_views_per_subscriber(video_data) == 0.0

    def test_missing_data(self):
        video_data = {}
        assert get_views_per_subscriber(video_data) == 0.0

    def test_none_vps(self):
        video_data = {
            "video": {"viewCount": 500, "calculated": {"viewsPerSubscriber": None}},
            "channel": {"subscriberCount": 100},
        }
        assert get_views_per_subscriber(video_data) == 5.0


class TestGetEngagementRate:
    def test_from_calculated(self):
        video_data = {
            "video": {"calculated": {"engagementRate": 3.5}},
        }
        assert get_engagement_rate(video_data) == 3.5

    def test_missing_data(self):
        video_data = {}
        assert get_engagement_rate(video_data) == 0.0

    def test_zero_rate(self):
        video_data = {
            "video": {"calculated": {"engagementRate": 0}},
        }
        assert get_engagement_rate(video_data) == 0.0

    def test_none_rate(self):
        video_data = {
            "video": {"calculated": {"engagementRate": None}},
        }
        assert get_engagement_rate(video_data) == 0.0


class TestGetContentType:
    def test_basic(self):
        video_data = {"title_analysis": {"contentSignals": {"contentType": "recipe"}}}
        assert get_content_type(video_data) == "recipe"

    def test_missing_analysis(self):
        assert get_content_type({}) == "unknown"

    def test_missing_content_type(self):
        video_data = {"title_analysis": {"contentSignals": {}}}
        assert get_content_type(video_data) == "unknown"


class TestGroupByContentType:
    def test_basic_grouping(self):
        videos = [
            {"title_analysis": {"contentSignals": {"contentType": "recipe"}}},
            {"title_analysis": {"contentSignals": {"contentType": "recipe"}}},
            {"title_analysis": {"contentSignals": {"contentType": "vlog"}}},
        ]
        groups = group_by_content_type(videos)
        assert len(groups["recipe"]) == 2
        assert len(groups["vlog"]) == 1

    def test_empty_list(self):
        groups = group_by_content_type([])
        assert groups == {}


class TestSplitTopPerformers:
    def test_basic_split(self):
        videos = []
        for vps in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]:
            videos.append(
                {
                    "video": {"calculated": {"viewsPerSubscriber": vps}},
                }
            )

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
        videos = [{"video": {"calculated": {"viewsPerSubscriber": 5.0}}} for _ in range(10)]
        all_vids, top_vids, threshold = split_top_performers(videos)
        assert len(all_vids) == 10
        # All have same vps, so all should be >= threshold
        assert len(top_vids) == 10

    def test_custom_metric_fn(self):
        videos = []
        for er in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            videos.append(
                {
                    "video": {"calculated": {"engagementRate": er}},
                }
            )

        all_vids, top_vids, threshold = split_top_performers(videos, metric_fn=get_engagement_rate)
        assert len(all_vids) == 10
        assert len(top_vids) >= 1
        assert threshold > 0


class TestRemoveOutliers:
    def test_removes_low_subscriber_channels(self):
        videos = [
            {"video": {"calculated": {"viewsPerSubscriber": 2.0}}, "channel": {"subscriberCount": 500}},  # Below min
            {"video": {"calculated": {"viewsPerSubscriber": 2.0}}, "channel": {"subscriberCount": 5000}},  # Above min
        ]
        filtered, stats = remove_outliers(videos, get_views_per_subscriber)
        assert len(filtered) == 1
        assert stats["removedLowSubscribers"] == 1

    def test_winsorization(self):
        videos = []
        for i in range(100):
            vps = 1.0 if i < 95 else 100.0  # 5 extreme outliers
            videos.append(
                {
                    "video": {"calculated": {"viewsPerSubscriber": vps}},
                    "channel": {"subscriberCount": 10000},
                }
            )

        filtered, stats = remove_outliers(videos, get_views_per_subscriber)
        assert stats["winsorizedCount"] > 0
        assert stats["vpsCap"] < 100.0

        # Verify VPS was actually capped
        for v in filtered:
            vps = v["video"]["calculated"]["viewsPerSubscriber"]
            assert vps <= stats["vpsCap"]

    def test_empty_videos(self):
        filtered, stats = remove_outliers([], get_views_per_subscriber)
        assert filtered == []
        assert stats["filteredCount"] == 0

    def test_custom_min_subscribers(self):
        videos = [
            {"video": {"calculated": {"viewsPerSubscriber": 2.0}}, "channel": {"subscriberCount": 500}},
        ]
        filtered, stats = remove_outliers(videos, get_views_per_subscriber, min_subscribers=100)
        assert len(filtered) == 1  # 500 > 100


class TestDescriptionExtraction:
    def test_extracts_description(self):
        analysis = {
            "contentSignals": {"contentType": "recipe"},
            "descriptionAnalysis": {
                "hasTimestamps": True,
                "linkCount": 3,
            },
        }
        result = _extract_description_analysis(analysis)
        assert result == {"hasTimestamps": True, "linkCount": 3}

    def test_missing_description(self):
        analysis = {"contentSignals": {"contentType": "recipe"}}
        result = _extract_description_analysis(analysis)
        assert result == {}

    def test_empty_description(self):
        analysis = {"descriptionAnalysis": {}}
        result = _extract_description_analysis(analysis)
        assert result == {}
