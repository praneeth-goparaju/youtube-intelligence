"""Tests for insights main module helper functions."""

import copy
import sys
from datetime import datetime, timedelta, timezone

import pytest

from insights.src import main as main_module
from insights.src.main import (
    get_views_per_subscriber,
    get_engagement_rate,
    get_content_type,
    group_by_content_type,
    profile_doc_name,
    split_top_performers,
    remove_outliers,
    generate_content_type_profile,
)
from insights.src.recommender_bridge import generate_recommender_documents


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

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Recipe", "recipe"),
            (" recipe ", "recipe"),
            ("list/top", "list_top"),
            ("List Top", "list_top"),
            ("list-top", "list_top"),
            ("", "unknown"),
            (None, "unknown"),
        ],
    )
    def test_normalized(self, raw, expected):
        assert get_content_type({"title_analysis": {"contentSignals": {"contentType": raw}}}) == expected

    def test_reserved_doc_names_prefixed(self):
        assert profile_doc_name("Summary") == "type_summary"
        assert profile_doc_name("timing") == "type_timing"
        assert profile_doc_name("list/top") == "list_top"


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

    def test_case_and_separator_variants_merge(self):
        videos = [
            {"title_analysis": {"contentSignals": {"contentType": ct}}}
            for ct in ["Recipe", "recipe", "list/top", "list_top"]
        ]
        groups = group_by_content_type(videos)
        assert {k: len(v) for k, v in groups.items()} == {"recipe": 2, "list_top": 2}


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
        assert threshold == 5.0
        # Top group is chosen by rank (ceil 10%), not `>= threshold`: ties don't inflate it.
        # With no id / uncapped VPS to break the tie, input order decides.
        assert top_vids == [videos[0]]

    def test_ties_at_winsorization_cap_do_not_inflate_top_group(self):
        # 20 of 100 videos share the global cap after winsorizing; the top 10% must still be
        # 10 videos, picked by the uncapped VPS tie-break.
        videos = []
        for i in range(100):
            vps = float(i + 1) if i < 80 else 1000.0 + i
            videos.append(
                {
                    "video_id": f"v{i:03d}",
                    "video": {"calculated": {"viewsPerSubscriber": vps}},
                    "channel": {"subscriberCount": 10000},
                }
            )
        capped, stats = remove_outliers(videos, get_views_per_subscriber, cap_percentile=80)
        assert stats["winsorizedCount"] == 20

        _, top, threshold = split_top_performers(capped)
        assert threshold == pytest.approx(280.0)  # p90 lands on the cap (p80 = 80 + 0.2 * 1000)
        assert stats["vpsCap"] == 280.0
        assert [v["video_id"] for v in top] == [f"v{i:03d}" for i in range(90, 100)]

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

    def test_derived_vps_is_capped(self):
        # Videos without a stored calculated.viewsPerSubscriber (VPS derived from views/subs)
        # must be capped too, and the capped value used everywhere downstream.
        videos = [
            {"video": {"viewCount": 10000 * (i + 1), "calculated": {}}, "channel": {"subscriberCount": 10000}}
            for i in range(20)
        ]
        filtered, stats = remove_outliers(videos, get_views_per_subscriber)
        assert stats["winsorizedCount"] == 1
        assert stats["vpsCap"] == 19.05
        assert max(get_views_per_subscriber(v) for v in filtered) == pytest.approx(19.05)
        assert filtered[-1]["video"]["calculated"]["viewsPerSubscriber"] == pytest.approx(19.05)
        assert videos[-1]["video"]["calculated"] == {}  # original untouched

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
                # One top video is too few to call the difference significant
                "hasTimestamps": {"all": 0.333, "top10": 1.0, "confidence": "low", "significant": False},
                "linkCount": {"all_avg": 4.0, "top10_avg": 6.0, "confidence": "low"},
            },
        }
        # Engagement profile splits by engagementRate (p90 of 1..4 = 3.7), not VPS
        engagement = profile["engagementProfile"]
        assert engagement["metric"] == "engagementRate"
        assert engagement["top10Threshold"] == 3.7
        assert engagement["top10Count"] == 1
        assert engagement["title"]["sampleSize"] == {"all": 4, "top10": 1}


def _title_video(i, vps, power_words, pattern_type, published_at=None):
    title_analysis = {
        "contentSignals": {"contentType": "recipe"},
        "structure": {"pattern": f"free text pattern {i}", "patternType": pattern_type},
        "hooks": {"powerWords": power_words},
        "descriptionAnalysis": {"hasTimestamps": i % 2 == 0},
    }
    return {
        "video_id": f"vid{i:03d}",
        "video": {"calculated": {"viewsPerSubscriber": vps}, "publishedAt": published_at},
        "title_analysis": title_analysis,
    }


class TestTitleProfileEndToEnd:
    def _videos(self):
        # 20 videos: 10 legacy (list powerWords), 10 title_description (comma-separated string).
        # The 2 top performers use patternType "question" and the power word "secret".
        videos = []
        for i in range(20):
            top = i >= 18
            words = ["secret", "best"] if top else ["easy"]
            if i % 2:
                words = ", ".join(words)
            videos.append(_title_video(i, 10.0 + i if top else 1.0, words, "question" if top else "segmented"))
        return videos

    def test_mixed_power_words_profile_and_bridge(self):
        profile = generate_content_type_profile("recipe", self._videos())
        title = profile["title"]

        # descriptionAnalysis is profiled only under "description", not duplicated in title
        assert "descriptionAnalysis" not in title["features"]
        assert "description" in profile
        assert title["features"]["hooks"]["powerWords"]["topItems"] == {
            "easy": {"all": 0.9, "top10": 0.0},
            "secret": {"all": 0.1, "top10": 1.0},
            "best": {"all": 0.1, "top10": 1.0},
        }
        assert title["patternPerformance"] == {
            "segmented": {"avgViewsPerSubscriber": 1.0, "count": 18},
            "question": {"avgViewsPerSubscriber": 28.5, "count": 2},
        }

        titles = generate_recommender_documents({"recipe": profile}, None)["titles"]
        assert titles["powerWords"] == {
            "highImpact": [{"word": "best", "multiplier": 10.0}, {"word": "secret", "multiplier": 10.0}]
        }
        assert titles["winningPatterns"] == [
            {"pattern": "question", "lift": 10.0, "avgViews": 28.5, "sampleSize": 2, "examples": []}
        ]

    def test_datetime_published_at_is_recency_weighted(self):
        # Firestore returns publishedAt as datetime; old videos must be down-weighted
        now = datetime.now(timezone.utc)
        videos = []
        for i in range(10):
            age_days = 0 if i < 5 else 3650  # ten half-lives -> weight ~0.001
            videos.append(
                {
                    "video": {
                        "calculated": {"viewsPerSubscriber": 1.0 + i},
                        "publishedAt": now - timedelta(days=age_days),
                    },
                    "title_analysis": {"contentSignals": {"contentType": "recipe"}, "score": 10 if i < 5 else 100},
                }
            )
        profile = generate_content_type_profile("recipe", videos)
        # Unweighted mean would be 55.0
        assert profile["title"]["features"]["score"]["all_avg"] == pytest.approx(10.09, abs=0.01)


class _FakeStore:
    """In-memory stand-in for the insights/ Firestore functions used by main()."""

    def __init__(self, videos=None, profiles=None):
        self.videos = videos or []
        self.profiles = profiles or {}
        self.writes = []

    def install(self, monkeypatch, tmp_path, argv):
        monkeypatch.setattr(main_module, "initialize_firebase", lambda: None)
        monkeypatch.setattr(
            main_module, "get_all_videos_with_analyses", lambda channel_id=None: copy.deepcopy(self.videos)
        )
        monkeypatch.setattr(main_module, "load_insight_profiles", lambda: copy.deepcopy(self.profiles))
        monkeypatch.setattr(main_module, "save_insights", lambda name, data: self.writes.append((name, data)))
        monkeypatch.setattr(main_module.config, "OUTPUTS_DIR", tmp_path)
        monkeypatch.setattr(sys, "argv", ["insights"] + argv)

    def written(self, name):
        return [data for doc, data in self.writes if doc == name]


def _gap_video(i):
    return {
        "video_id": f"v{i:03d}",
        "channel": {"subscriberCount": 10000},
        "video": {"calculated": {"viewsPerSubscriber": 1.0 + (i % 5)}},
        "title_analysis": {
            "contentSignals": {"contentType": "Recipe", "isRecipe": True},
            "keywords": {"niche": "cooking", "primaryKeyword": f"kw{i % 3}", "secondaryKeywords": "biryani, spicy"},
            "structure": {"patternType": "segmented"},
        },
    }


class TestMainWrites:
    def test_bridge_only_refuses_without_stored_profiles(self, monkeypatch, tmp_path):
        # Videos exist, but bridge-only mode has no stored profiles to transform
        store = _FakeStore(videos=[_gap_video(i) for i in range(40)])
        store.install(monkeypatch, tmp_path, ["--type", "bridge"])
        with pytest.raises(SystemExit) as exc:
            main_module.main()
        assert exc.value.code == 1
        assert store.writes == []

    def test_bridge_only_uses_stored_profiles(self, monkeypatch, tmp_path):
        profile = {
            "contentType": "recipe",
            "summary": {"totalVideos": 100},
            "timing": {
                "bestDays": [{"day": "Saturday", "avgViewsPerSubscriber": 3.0, "videoCount": 50}],
                "bestHours": [{"hour": 18, "avgViewsPerSubscriber": 3.0, "videoCount": 30}],
            },
        }
        store = _FakeStore(profiles={"recipe": profile})
        store.install(monkeypatch, tmp_path, ["--type", "bridge"])
        main_module.main()

        # contentGaps and summary are not touched in bridge-only mode
        assert sorted(name for name, _ in store.writes) == ["thumbnails", "timing", "titles"]
        timing = store.written("timing")[0]
        assert timing["basedOnVideos"] == 100
        assert timing["bestTimes"]["optimal"]["day"] == "Saturday"

    @pytest.mark.parametrize("run_type", ["gaps", "all"])
    def test_content_gaps_written_once_in_recommender_shape(self, monkeypatch, tmp_path, run_type):
        store = _FakeStore(videos=[_gap_video(i) for i in range(40)])
        store.install(monkeypatch, tmp_path, ["--type", run_type])
        main_module.main()

        docs = store.written("contentGaps")
        assert len(docs) == 1
        doc = docs[0]
        assert "contentGaps" not in doc
        assert doc["highOpportunity"][0]["topic"] == "cooking"
        assert set(doc["highOpportunity"][0]) == {"topic", "avgViews", "videoCount", "opportunityScore"}
        assert doc["saturatedTopics"] == []
        assert set(doc["keywordGaps"]) == {"highValueKeywords", "totalKeywords"}
        assert doc["keywordGaps"]["totalKeywords"] == 5
        assert doc["formatGaps"]["formatPerformance"][0]["format"] == "recipe"
        assert set(doc["formatGaps"]) == {"formatPerformance", "recommendedFormats"}
        if run_type == "all":
            # Profile doc uses the normalized content type
            assert len(store.written("recipe")) == 1
            assert len(store.written("titles")) == 1
