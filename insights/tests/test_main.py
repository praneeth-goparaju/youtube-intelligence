"""Tests for insights main module helper functions."""

import copy

import pytest

from insights.src.main import (
    get_views_per_subscriber,
    get_engagement_rate,
    get_content_type,
    group_by_content_type,
    split_top_performers,
    remove_outliers,
    generate_content_type_profile,
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

    @pytest.mark.parametrize(
        "video_data",
        [
            {},
            {"video": {"calculated": {"engagementRate": 0}}},
            {"video": {"calculated": {"engagementRate": None}}},
        ],
        ids=["missing", "zero", "none"],
    )
    def test_falsy_rate_is_zero(self, video_data):
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
        assert all_vids is videos
        # np.percentile linear interpolation: 9 + 0.1 * (10 - 9) = 9.1
        assert threshold == 9.1
        assert top_vids == [videos[9]]

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
        assert all_vids is videos
        # 0.9 + 0.1 * (1.0 - 0.9) = 0.91
        assert threshold == pytest.approx(0.91)
        assert top_vids == [videos[9]]


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
        original = copy.deepcopy(videos)

        filtered, stats = remove_outliers(videos, get_views_per_subscriber)
        # Capping happens on copies: caller's list and video dicts are untouched
        assert videos == original
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


def _profile_video(vps, engagement, description):
    title_analysis = {"contentSignals": {"contentType": "recipe"}, "descriptionAnalysis": description}
    return {
        "video": {"calculated": {"viewsPerSubscriber": vps, "engagementRate": engagement}},
        "title_analysis": title_analysis,
    }


class TestGenerateContentTypeProfile:
    def test_description_and_engagement_sections(self):
        videos = [
            _profile_video(1.0, 1.0, {"hasTimestamps": False, "linkCount": 2}),
            _profile_video(2.0, 2.0, {"hasTimestamps": False, "linkCount": 4}),
            _profile_video(10.0, 3.0, {"hasTimestamps": True, "linkCount": 6}),  # VPS top performer
            _profile_video(3.0, 4.0, None),  # engagement top performer, no description analysis
        ]

        profile = generate_content_type_profile("recipe", videos)

        # Description section comes from title_analysis.descriptionAnalysis; the None entry is skipped
        assert profile["description"] == {
            "sampleSize": {"all": 3, "top10": 1},
            "features": {
                "hasTimestamps": {"all": 0.333, "top10": 1.0, "confidence": "low", "significant": True},
                "linkCount": {"all_avg": 4.0, "top10_avg": 6.0, "confidence": "low"},
            },
        }
        # Engagement profile splits by engagementRate (p90 of 1..4 = 3.7), not VPS
        engagement = profile["engagementProfile"]
        assert engagement["metric"] == "engagementRate"
        assert engagement["top10Threshold"] == 3.7
        assert engagement["top10Count"] == 1
        assert engagement["title"]["sampleSize"] == {"all": 4, "top10": 1}
