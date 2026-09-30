"""Tests for the content gap analysis module."""

import pytest

from insights.src.gaps import (
    GapAnalyzer,
    MIN_VIDEOS_FOR_TOPIC,
    MIN_VIDEOS_FOR_KEYWORD,
)


def make_video(niche="cooking", sub_niche="", primary_kw="biryani", secondary_kws=None, vps=1.0, content_signals=None):
    """Helper to create a video dict matching the expected structure."""
    keywords = {
        "niche": niche,
        "subNiche": sub_niche,
        "primaryKeyword": primary_kw,
        "secondaryKeywords": secondary_kws or [],
    }
    signals = content_signals or {"contentType": "recipe"}
    return {
        "title_analysis": {
            "keywords": keywords,
            "contentSignals": signals,
        },
        "_vps": vps,
    }


def get_vps(video):
    """Extract viewsPerSubscriber from test video dict."""
    return video.get("_vps", 0)


class TestFindContentGaps:
    def test_basic_gap_detection(self):
        videos = []
        # 5 cooking videos with high vps
        for _ in range(5):
            videos.append(make_video(niche="cooking", vps=10.0))
        # 5 vlog videos with low vps
        for _ in range(5):
            videos.append(make_video(niche="vlog", vps=1.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()

        assert result["totalTopics"] == 2
        # score = avg / (count + 1) = 10 / 6; contentShare is a percent
        assert result["highOpportunity"][0] == {
            "topic": "cooking",
            "avgViewsPerSubscriber": 10.0,
            "videoCount": 5,
            "contentShare": 50.0,
            "opportunityScore": 1.667,
        }

    def test_minimum_videos_required(self):
        # Only 2 videos per topic (below MIN_VIDEOS_FOR_TOPIC=3)
        videos = [
            make_video(niche="cooking", vps=5.0),
            make_video(niche="cooking", vps=5.0),
        ]
        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()
        assert result["totalTopics"] == 0

    def test_sub_niche_grouping(self):
        videos = []
        for _ in range(MIN_VIDEOS_FOR_TOPIC):
            videos.append(make_video(niche="cooking", sub_niche="biryani", vps=5.0))
        for _ in range(MIN_VIDEOS_FOR_TOPIC):
            videos.append(make_video(niche="cooking", sub_niche="curry", vps=3.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()

        topics = [opp["topic"] for opp in result["highOpportunity"]]
        assert "cooking/biryani" in topics
        assert "cooking/curry" in topics

    def test_opportunity_score_ordering(self):
        videos = []
        # High vps, low count = high opportunity
        for _ in range(MIN_VIDEOS_FOR_TOPIC):
            videos.append(make_video(niche="rare_topic", vps=50.0))
        # Low vps, high count = low opportunity
        for _ in range(20):
            videos.append(make_video(niche="common_topic", vps=1.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()

        # rare: 50 / 4 = 12.5 beats common: 1 / 21
        assert [opp["topic"] for opp in result["highOpportunity"]] == ["rare_topic", "common_topic"]

    def test_zero_vps_excluded(self):
        videos = [make_video(niche="cooking", vps=0) for _ in range(10)]
        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()
        assert result["avgViewsPerSubscriber"] == 0
        assert result["totalTopics"] == 0

    def test_saturation_detection(self):
        videos = []
        # 60% of videos are "cooking" with below-average vps
        for _ in range(60):
            videos.append(make_video(niche="cooking", vps=0.5))
        # 40% of videos are "tech" with above-average vps
        for _ in range(40):
            videos.append(make_video(niche="tech", vps=5.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()

        saturated_topics = [t["topic"] for t in result["saturatedTopics"]]
        assert "cooking" in saturated_topics


class TestAnalyzeKeywordGaps:
    def test_basic_keyword_analysis(self):
        videos = []
        for _ in range(5):
            videos.append(make_video(primary_kw="biryani", vps=10.0))
        for _ in range(50):
            videos.append(make_video(primary_kw="chicken", vps=2.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_keyword_gaps()

        assert result["totalKeywords"] == 2
        # overall avg = 150 / 55; usageRate is a percent: 5 / 55 * 100
        assert result["highValueKeywords"] == [
            {
                "keyword": "biryani",
                "avgViewsPerSubscriber": 10.0,
                "viewsMultiplier": 3.67,
                "usageCount": 5,
                "usageRate": 9.09,
            }
        ]

    @pytest.mark.parametrize(
        "secondary, expected_total",
        [
            (["spicy", "traditional"], 3),
            # Comma-separated string must split into keywords, not iterate char-by-char
            ("spicy, traditional, homestyle", 4),
        ],
        ids=["list", "string"],
    )
    def test_secondary_keywords_included(self, secondary, expected_total):
        videos = [make_video(primary_kw="food", secondary_kws=secondary, vps=5.0) for _ in range(5)]

        result = GapAnalyzer(videos, get_vps).analyze_keyword_gaps()

        assert result["totalKeywords"] == expected_total

    @pytest.mark.parametrize("count", [MIN_VIDEOS_FOR_KEYWORD - 1, MIN_VIDEOS_FOR_KEYWORD])
    def test_minimum_keyword_count(self, count):
        # Low-VPS filler keeps "rare" above average and under the usage threshold,
        # so the minimum-count rule is the only thing that can exclude it.
        videos = [make_video(primary_kw="filler", vps=1.0) for _ in range(30)]
        videos += [make_video(primary_kw="rare", vps=100.0) for _ in range(count)]

        result = GapAnalyzer(videos, get_vps).analyze_keyword_gaps()

        keywords = [kw["keyword"] for kw in result["highValueKeywords"]]
        assert keywords == (["rare"] if count >= MIN_VIDEOS_FOR_KEYWORD else [])

    def test_keyword_case_normalization(self):
        videos = []
        for _ in range(MIN_VIDEOS_FOR_KEYWORD):
            videos.append(make_video(primary_kw="Biryani", vps=5.0))
        for _ in range(MIN_VIDEOS_FOR_KEYWORD):
            videos.append(make_video(primary_kw="biryani", vps=5.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_keyword_gaps()
        # "Biryani" and "biryani" should be normalized to the same keyword
        assert result["totalKeywords"] == 1


class TestAnalyzeFormatGaps:
    def test_multiplier_ordering(self):
        videos = []
        # Recipes perform well
        for _ in range(5):
            videos.append(make_video(content_signals={"isRecipe": True, "contentType": "recipe"}, vps=10.0))
        # Vlogs perform poorly
        for _ in range(5):
            videos.append(make_video(content_signals={"isVlog": True, "contentType": "vlog"}, vps=1.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_format_gaps()

        formats = result["formatPerformance"]
        assert [fmt["format"] for fmt in formats] == ["recipe", "vlog"]
        # overall avg = 5.5, recipe avg = 10 -> 10 / 5.5
        assert formats[0]["viewsMultiplier"] == 1.82

    def test_recommended_formats_above_average(self):
        videos = []
        for _ in range(5):
            videos.append(make_video(content_signals={"isRecipe": True, "contentType": "recipe"}, vps=10.0))
        for _ in range(5):
            videos.append(make_video(content_signals={"isVlog": True, "contentType": "vlog"}, vps=1.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_format_gaps()

        assert [fmt["format"] for fmt in result["recommendedFormats"]] == ["recipe"]

    def test_empty_videos(self):
        analyzer = GapAnalyzer([], get_vps)
        result = analyzer.analyze_format_gaps()
        assert result["formatPerformance"] == []
        assert result["recommendedFormats"] == []
