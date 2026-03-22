"""Tests for the recommender bridge module."""

from insights.src.recommender_bridge import (
    generate_recommender_documents,
    _build_thumbnail_insights,
    _build_title_insights,
    _build_timing_insights,
    _build_content_gap_insights,
    _get_hour_label,
    _get_thumbnail_category,
    _weighted_avg,
)


def _make_profile(content_type="recipe", total=100, top10=10, thumb_features=None, title_features=None, timing=None):
    """Helper to build a minimal profile dict."""
    profile = {
        "contentType": content_type,
        "generatedAt": "2026-03-04T00:00:00+00:00",
        "summary": {
            "totalVideos": total,
            "top10Count": top10,
            "top10Threshold": 5.0,
            "avgViewsPerSubscriber": 2.0,
        },
    }
    if thumb_features is not None:
        profile["thumbnail"] = {
            "sampleSize": {"all": total, "top10": top10},
            "features": thumb_features,
        }
    if title_features is not None:
        profile["title"] = {
            "sampleSize": {"all": total, "top10": top10},
            "features": title_features,
        }
    if timing is not None:
        profile["timing"] = timing
    else:
        profile["timing"] = {"bestDays": [], "bestHours": []}
    return profile


class TestBuildThumbnailInsights:
    def test_basic_structure(self):
        profiles = {
            "recipe": _make_profile(
                thumb_features={
                    "humanPresence": {
                        "hasFace": {
                            "all": 0.4,
                            "top10": 0.8,
                            "confidence": "high",
                            "significant": True,
                        },
                    },
                    "food": {
                        "hasFood": {
                            "all": 0.6,
                            "top10": 0.9,
                            "confidence": "high",
                            "significant": True,
                        },
                    },
                }
            ),
        }
        result = _build_thumbnail_insights(profiles, "2026-03-04T00:00:00Z", 100)

        assert "generatedAt" in result
        assert "basedOnVideos" in result
        assert "topPerformingElements" in result
        assert isinstance(result["topPerformingElements"], dict)

    def test_categories_mapped_correctly(self):
        profiles = {
            "recipe": _make_profile(
                thumb_features={
                    "humanPresence": {
                        "hasFace": {
                            "all": 0.3,
                            "top10": 0.8,
                            "confidence": "high",
                            "significant": True,
                        },
                    },
                    "colors": {
                        "isBright": {
                            "all": 0.4,
                            "top10": 0.7,
                            "confidence": "high",
                            "significant": True,
                        },
                    },
                    "scene": {
                        "isOutdoor": {
                            "all": 0.2,
                            "top10": 0.5,
                            "confidence": "high",
                            "significant": True,
                        },
                    },
                }
            ),
        }
        result = _build_thumbnail_insights(profiles, "2026-03-04T00:00:00Z", 100)
        elements = result["topPerformingElements"]

        # humanPresence should stay humanPresence
        assert "humanPresence" in elements
        # colors should stay colors
        assert "colors" in elements
        # scene maps to composition
        assert "composition" in elements

    def test_worst_performing(self):
        profiles = {
            "recipe": _make_profile(
                thumb_features={
                    "humanPresence": {
                        "hasCartoon": {
                            "all": 0.5,
                            "top10": 0.1,  # Low lift = worst
                            "confidence": "high",
                            "significant": True,
                        },
                    },
                }
            ),
        }
        result = _build_thumbnail_insights(profiles, "2026-03-04T00:00:00Z", 100)
        assert "worstPerformingElements" in result

    def test_lift_computation(self):
        profiles = {
            "recipe": _make_profile(
                thumb_features={
                    "food": {
                        "hasCloseUp": {
                            "all": 0.25,
                            "top10": 0.75,
                            "confidence": "high",
                            "significant": True,
                        },
                    },
                }
            ),
        }
        result = _build_thumbnail_insights(profiles, "2026-03-04T00:00:00Z", 100)

        if "food" in result["topPerformingElements"]:
            elements = result["topPerformingElements"]["food"]
            # lift = 0.75 / 0.25 = 3.0
            assert elements[0]["lift"] == 3.0


class TestBuildTitleInsights:
    def test_basic_structure(self):
        profiles = {
            "recipe": _make_profile(
                title_features={
                    "structure": {
                        "pattern": {
                            "all": {"question": 0.3, "statement": 0.7},
                            "top10": {"question": 0.6, "statement": 0.4},
                            "confidence": "high",
                        },
                        "characterCount": {
                            "all_avg": 45.0,
                            "top10_avg": 50.0,
                            "confidence": "high",
                        },
                        "wordCount": {
                            "all_avg": 8.0,
                            "top10_avg": 9.0,
                            "confidence": "high",
                        },
                    },
                }
            ),
        }
        result = _build_title_insights(profiles, "2026-03-04T00:00:00Z", 100)

        assert "generatedAt" in result
        assert "basedOnVideos" in result

    def test_winning_patterns(self):
        profiles = {
            "recipe": _make_profile(
                title_features={
                    "structure": {
                        "pattern": {
                            "all": {"question": 0.2, "howto": 0.3, "list": 0.5},
                            "top10": {"question": 0.5, "howto": 0.3, "list": 0.2},
                            "confidence": "high",
                        },
                    },
                }
            ),
        }
        result = _build_title_insights(profiles, "2026-03-04T00:00:00Z", 100)

        if "winningPatterns" in result:
            patterns = result["winningPatterns"]
            assert isinstance(patterns, list)
            for p in patterns:
                assert "pattern" in p
                assert "avgViews" in p
                assert "sampleSize" in p

    def test_optimal_length(self):
        profiles = {
            "recipe": _make_profile(
                title_features={
                    "structure": {
                        "characterCount": {
                            "all_avg": 45.0,
                            "top10_avg": 55.0,
                            "confidence": "high",
                        },
                        "wordCount": {
                            "all_avg": 8.0,
                            "top10_avg": 10.0,
                            "confidence": "high",
                        },
                    },
                }
            ),
        }
        result = _build_title_insights(profiles, "2026-03-04T00:00:00Z", 100)

        if "optimalLength" in result:
            opt = result["optimalLength"]
            assert "characters" in opt
            assert "words" in opt
            assert "sweetSpot" in opt["characters"]

    def test_optimal_language_mix(self):
        profiles = {
            "recipe": _make_profile(
                title_features={
                    "language": {
                        "teluguRatio": {
                            "all_avg": 0.4,
                            "top10_avg": 0.6,
                            "confidence": "high",
                        },
                    },
                }
            ),
        }
        result = _build_title_insights(profiles, "2026-03-04T00:00:00Z", 100)

        if "optimalLanguageMix" in result:
            mix = result["optimalLanguageMix"]
            assert "teluguRatio" in mix
            assert mix["teluguRatio"]["sweetSpot"] == 0.6


class TestBuildTimingInsights:
    def test_basic_structure(self):
        profiles = {
            "recipe": _make_profile(
                timing={
                    "bestDays": [
                        {"day": "Saturday", "avgViewsPerSubscriber": 3.0, "videoCount": 50},
                        {"day": "Sunday", "avgViewsPerSubscriber": 2.5, "videoCount": 40},
                    ],
                    "bestHours": [
                        {"hour": 18, "avgViewsPerSubscriber": 3.5, "videoCount": 30},
                        {"hour": 12, "avgViewsPerSubscriber": 2.0, "videoCount": 25},
                    ],
                }
            ),
        }
        result = _build_timing_insights(profiles, "2026-03-04T00:00:00Z", 100)

        assert "bestTimes" in result
        assert "byDayOfWeek" in result["bestTimes"]
        assert "byHourIST" in result["bestTimes"]
        assert "optimal" in result["bestTimes"]

    def test_multiplier_calculation(self):
        profiles = {
            "recipe": _make_profile(
                timing={
                    "bestDays": [
                        {"day": "Saturday", "avgViewsPerSubscriber": 4.0, "videoCount": 50},
                        {"day": "Monday", "avgViewsPerSubscriber": 2.0, "videoCount": 50},
                    ],
                    "bestHours": [],
                }
            ),
        }
        result = _build_timing_insights(profiles, "2026-03-04T00:00:00Z", 100)

        days = result["bestTimes"]["byDayOfWeek"]
        assert len(days) == 2
        # Saturday should have higher multiplier
        sat = next(d for d in days if d["day"] == "Saturday")
        mon = next(d for d in days if d["day"] == "Monday")
        assert sat["multiplier"] > mon["multiplier"]

    def test_optimal_selection(self):
        profiles = {
            "recipe": _make_profile(
                timing={
                    "bestDays": [
                        {"day": "Saturday", "avgViewsPerSubscriber": 4.0, "videoCount": 50},
                        {"day": "Monday", "avgViewsPerSubscriber": 2.0, "videoCount": 50},
                    ],
                    "bestHours": [
                        {"hour": 18, "avgViewsPerSubscriber": 3.0, "videoCount": 30},
                        {"hour": 10, "avgViewsPerSubscriber": 1.0, "videoCount": 30},
                    ],
                }
            ),
        }
        result = _build_timing_insights(profiles, "2026-03-04T00:00:00Z", 100)

        optimal = result["bestTimes"]["optimal"]
        assert optimal["day"] == "Saturday"
        assert optimal["hourIST"] == 18
        assert optimal["multiplier"] > 1.0

    def test_hour_labels(self):
        profiles = {
            "recipe": _make_profile(
                timing={
                    "bestDays": [],
                    "bestHours": [
                        {"hour": 8, "avgViewsPerSubscriber": 2.0, "videoCount": 20},
                        {"hour": 14, "avgViewsPerSubscriber": 2.0, "videoCount": 20},
                        {"hour": 19, "avgViewsPerSubscriber": 2.0, "videoCount": 20},
                        {"hour": 23, "avgViewsPerSubscriber": 2.0, "videoCount": 20},
                    ],
                }
            ),
        }
        result = _build_timing_insights(profiles, "2026-03-04T00:00:00Z", 100)

        hours = result["bestTimes"]["byHourIST"]
        labels = {h["hour"]: h["label"] for h in hours}
        assert labels[8] == "Morning"
        assert labels[14] == "Afternoon"
        assert labels[19] == "Evening"
        assert labels[23] == "Night"

    def test_empty_timing(self):
        profiles = {
            "recipe": _make_profile(timing={"bestDays": [], "bestHours": []}),
        }
        result = _build_timing_insights(profiles, "2026-03-04T00:00:00Z", 100)
        assert result["bestTimes"]["byDayOfWeek"] == []
        assert result["bestTimes"]["byHourIST"] == []
        assert result["bestTimes"]["optimal"] == {}


class TestBuildContentGapInsights:
    def test_flat_structure(self):
        content_gaps = {
            "generatedAt": "2026-03-04T00:00:00Z",
            "totalVideos": 100,
            "contentGaps": {
                "highOpportunity": [
                    {
                        "topic": "cooking/biryani",
                        "avgViewsPerSubscriber": 5.0,
                        "videoCount": 10,
                        "opportunityScore": 2.5,
                    },
                ],
                "saturatedTopics": [
                    {
                        "topic": "cooking/general",
                        "contentShare": 30.0,
                    },
                ],
            },
        }

        result = _build_content_gap_insights(content_gaps, "2026-03-04T00:00:00Z")

        # Should be flat (no nesting under 'contentGaps')
        assert "highOpportunity" in result
        assert "saturatedTopics" in result
        assert "contentGaps" not in result

    def test_avg_views_mapping(self):
        content_gaps = {
            "contentGaps": {
                "highOpportunity": [
                    {
                        "topic": "test",
                        "avgViewsPerSubscriber": 3.0,
                        "videoCount": 5,
                        "opportunityScore": 1.5,
                    },
                ],
                "saturatedTopics": [],
            },
        }

        result = _build_content_gap_insights(content_gaps, "2026-03-04T00:00:00Z")
        assert result["highOpportunity"][0]["avgViews"] == 3.0

    def test_saturated_topic_competition(self):
        content_gaps = {
            "contentGaps": {
                "highOpportunity": [],
                "saturatedTopics": [
                    {"topic": "cooking", "contentShare": 30.0},
                    {"topic": "vlogs", "contentShare": 10.0},
                ],
            },
        }

        result = _build_content_gap_insights(content_gaps, "2026-03-04T00:00:00Z")

        for topic in result["saturatedTopics"]:
            assert "topic" in topic
            assert "competition" in topic

        # contentShare > 20 → 'high', otherwise 'medium'
        assert result["saturatedTopics"][0]["competition"] == "high"
        assert result["saturatedTopics"][1]["competition"] == "medium"


class TestGenerateRecommenderDocuments:
    def test_all_four_docs_present(self):
        profiles = {
            "recipe": _make_profile(
                thumb_features={
                    "humanPresence": {
                        "hasFace": {
                            "all": 0.3,
                            "top10": 0.8,
                            "confidence": "high",
                            "significant": True,
                        },
                    },
                },
                title_features={
                    "structure": {
                        "characterCount": {
                            "all_avg": 45.0,
                            "top10_avg": 50.0,
                            "confidence": "high",
                        },
                    },
                },
                timing={
                    "bestDays": [
                        {"day": "Saturday", "avgViewsPerSubscriber": 3.0, "videoCount": 50},
                    ],
                    "bestHours": [
                        {"hour": 18, "avgViewsPerSubscriber": 3.0, "videoCount": 30},
                    ],
                },
            ),
        }
        content_gaps = {
            "contentGaps": {
                "highOpportunity": [
                    {"topic": "test", "avgViewsPerSubscriber": 5.0, "videoCount": 10, "opportunityScore": 2.0}
                ],
                "saturatedTopics": [{"topic": "general", "contentShare": 30.0}],
            },
        }

        result = generate_recommender_documents(profiles, content_gaps)

        assert "thumbnails" in result
        assert "titles" in result
        assert "timing" in result
        assert "contentGaps" in result

    def test_without_content_gaps(self):
        profiles = {"recipe": _make_profile()}
        result = generate_recommender_documents(profiles, None)

        assert "thumbnails" in result
        assert "titles" in result
        assert "timing" in result
        assert "contentGaps" not in result

    def test_empty_profiles(self):
        result = generate_recommender_documents({}, None)
        assert "thumbnails" in result
        assert result["thumbnails"]["basedOnVideos"] == 0


class TestHelpers:
    def test_get_hour_label(self):
        assert _get_hour_label(6) == "Morning"
        assert _get_hour_label(11) == "Morning"
        assert _get_hour_label(12) == "Afternoon"
        assert _get_hour_label(16) == "Afternoon"
        assert _get_hour_label(17) == "Evening"
        assert _get_hour_label(21) == "Evening"
        assert _get_hour_label(22) == "Night"
        assert _get_hour_label(5) == "Night"
        assert _get_hour_label(0) == "Night"

    def test_get_thumbnail_category(self):
        assert _get_thumbnail_category("humanPresence.hasFace") == "humanPresence"
        assert _get_thumbnail_category("food.hasFood") == "food"
        assert _get_thumbnail_category("colors.isBright") == "colors"
        assert _get_thumbnail_category("textElements.hasText") == "text"
        assert _get_thumbnail_category("scene.isOutdoor") == "composition"
        assert _get_thumbnail_category("unknownSection.field") == "composition"

    def test_weighted_avg(self):
        assert _weighted_avg([]) == 0.0
        assert _weighted_avg([(10, 1), (20, 1)]) == 15.0
        assert _weighted_avg([(10, 1), (20, 3)]) == 17.5
