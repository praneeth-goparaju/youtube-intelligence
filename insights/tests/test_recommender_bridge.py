"""Tests for the recommender bridge module."""

from insights.src.recommender_bridge import (
    generate_recommender_documents,
    _build_thumbnail_insights,
    _build_title_insights,
    _build_timing_insights,
    _build_content_gap_insights,
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
                    "textElements": {
                        "hasText": {"all": 0.4, "top10": 0.8, "confidence": "high", "significant": True},
                    },
                    "food": {
                        "hasFood": {"all": 0.5, "top10": 0.9, "confidence": "high", "significant": True},
                    },
                    "unknownSection": {
                        "field": {"all": 0.2, "top10": 0.6, "confidence": "high", "significant": True},
                    },
                }
            ),
        }
        result = _build_thumbnail_insights(profiles, "2026-03-04T00:00:00Z", 100)
        by_category = {
            category: [e["element"] for e in elements] for category, elements in result["topPerformingElements"].items()
        }

        # textElements -> text; scene and unmapped sections -> composition (sorted by lift: 3.0, 2.5)
        assert by_category == {
            "humanPresence": ["humanPresence.hasFace"],
            "colors": ["colors.isBright"],
            "text": ["textElements.hasText"],
            "food": ["food.hasFood"],
            "composition": ["unknownSection.field", "scene.isOutdoor"],
        }

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
        # lift = 0.1 / 0.5 = 0.2 < 0.7 -> flagged to avoid, not listed as top performing
        assert result["topPerformingElements"] == {}
        assert result["worstPerformingElements"] == [
            {"element": "humanPresence.hasCartoon", "lift": 0.2, "sampleSize": 100, "avoid": True}
        ]

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
                    "textElements": {
                        "words": {
                            "all_avg_count": 1.0,
                            "top10_avg_count": 2.0,
                            "confidence": "high",
                            "topItems": {"tasty": {"all": 0.2, "top10": 0.9}},
                        },
                    },
                    "humanPresence": {
                        # Low confidence / not significant: both filtered out
                        "hasHands": {"all": 0.2, "top10": 0.9, "confidence": "low", "significant": True},
                        "hasFace": {"all": 0.2, "top10": 0.9, "confidence": "high", "significant": False},
                    },
                }
            ),
        }
        result = _build_thumbnail_insights(profiles, "2026-03-04T00:00:00Z", 100)

        # lift = 0.75 / 0.25 = 3.0 (list topItems of textElements.words are not elements)
        assert result == {
            "generatedAt": "2026-03-04T00:00:00Z",
            "basedOnVideos": 100,
            "topPerformingElements": {"food": [{"element": "food.hasCloseUp", "lift": 3.0, "sampleSize": 100}]},
            "worstPerformingElements": [],
        }


class TestBuildTitleInsights:
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

        # Only "question" is over-represented in the top 10% (lift 2.5); howto (1.0) and
        # list (0.4) are excluded. No patternPerformance -> avgViews is omitted (unknown),
        # never filled with the lift.
        assert result["winningPatterns"] == [{"pattern": "question", "lift": 2.5, "sampleSize": 20, "examples": []}]

    def test_winning_patterns_use_pattern_type_and_matching_denominators(self):
        # structure.pattern is free text (dropped by the profiler); patternType is categorical.
        # The "vlog" profile has no pattern stats and must not dilute the top10 denominator.
        recipe = _make_profile(
            total=100,
            top10=10,
            title_features={
                "structure": {
                    "patternType": {
                        "all": {"question": 0.2, "segmented": 0.8},
                        "top10": {"question": 0.4, "segmented": 0.6},
                        "confidence": "medium",
                    },
                },
            },
        )
        recipe["title"]["patternPerformance"] = {
            "question": {"avgViewsPerSubscriber": 3.0, "count": 20},
            "segmented": {"avgViewsPerSubscriber": 1.0, "count": 80},
        }
        vlog = _make_profile(content_type="vlog", total=300, top10=30, title_features={})
        result = _build_title_insights({"recipe": recipe, "vlog": vlog}, "2026-03-04T00:00:00Z", 400)

        assert result["winningPatterns"] == [
            {"pattern": "question", "lift": 2.0, "avgViews": 3.0, "sampleSize": 20, "examples": []}
        ]

    def test_power_words_split_by_impact(self):
        profiles = {
            "recipe": _make_profile(
                title_features={
                    "hooks": {
                        "powerWords": {
                            "all_avg_count": 1.0,
                            "top10_avg_count": 1.5,
                            "confidence": "medium",
                            "topItems": {
                                "secret": {"all": 0.1, "top10": 0.3},
                                "best": {"all": 0.2, "top10": 0.25},
                                "easy": {"all": 0.3, "top10": 0.1},
                            },
                        },
                    },
                },
            ),
        }
        result = _build_title_insights(profiles, "2026-03-04T00:00:00Z", 100)
        assert result["powerWords"] == {
            "highImpact": [{"word": "secret", "multiplier": 3.0}],
            "mediumImpact": [{"word": "best", "multiplier": 1.25}],
        }

    def test_optimal_length(self):
        # Two content types with unequal top10 sample sizes (10 vs 30): sweet spot is the
        # sample-weighted top10 average, e.g. (40*10 + 80*30) / 40 = 70 (unweighted would be 60).
        profiles = {
            "recipe": _make_profile(
                top10=10,
                title_features={
                    "structure": {
                        "characterCount": {"all_avg": 35.0, "top10_avg": 40.0, "confidence": "high"},
                        "wordCount": {"all_avg": 7.0, "top10_avg": 8.0, "confidence": "high"},
                    },
                },
            ),
            "vlog": _make_profile(
                content_type="vlog",
                top10=30,
                title_features={
                    "structure": {
                        "characterCount": {"all_avg": 60.0, "top10_avg": 80.0, "confidence": "high"},
                        "wordCount": {"all_avg": 10.0, "top10_avg": 12.0, "confidence": "high"},
                    },
                },
            ),
        }
        result = _build_title_insights(profiles, "2026-03-04T00:00:00Z", 200)

        # min/max = sweetSpot * 0.7 / 1.3, rounded
        assert result["optimalLength"] == {
            "characters": {"min": 49.0, "max": 91.0, "sweetSpot": 70.0},
            "words": {"min": 8.0, "max": 14.0, "sweetSpot": 11.0},
        }

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

        assert result["optimalLanguageMix"] == {"teluguRatio": {"min": 0.45, "max": 0.75, "sweetSpot": 0.6}}


class TestBuildTimingInsights:
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

        # Saturday 4 / 3 = 1.33, 18h 3 / 2 = 1.5 -> combined round(1.33 * 1.5, 2)
        assert result["bestTimes"]["optimal"] == {
            "day": "Saturday",
            "hourIST": 18,
            "description": "Evening",
            "multiplier": 2.0,
        }

    def test_hour_labels(self):
        boundaries = {
            0: "Night",
            5: "Night",
            6: "Morning",
            11: "Morning",
            12: "Afternoon",
            16: "Afternoon",
            17: "Evening",
            21: "Evening",
            22: "Night",
        }
        profiles = {
            "recipe": _make_profile(
                timing={
                    "bestDays": [],
                    "bestHours": [
                        {"hour": hour, "avgViewsPerSubscriber": 2.0, "videoCount": 20} for hour in boundaries
                    ],
                }
            ),
        }
        result = _build_timing_insights(profiles, "2026-03-04T00:00:00Z", 100)

        labels = {h["hour"]: h["label"] for h in result["bestTimes"]["byHourIST"]}
        assert labels == boundaries

    def test_empty_timing(self):
        profiles = {
            "recipe": _make_profile(timing={"bestDays": [], "bestHours": []}),
        }
        result = _build_timing_insights(profiles, "2026-03-04T00:00:00Z", 100)
        assert result["bestTimes"]["byDayOfWeek"] == []
        assert result["bestTimes"]["byHourIST"] == []
        assert result["bestTimes"]["optimal"] == {}


class TestBuildContentGapInsights:
    def test_recommender_shape(self):
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

        content_gaps["contentGaps"].update({"totalTopics": 12, "avgViewsPerSubscriber": 1.5})
        keyword = {
            "keyword": "biryani",
            "avgViewsPerSubscriber": 4.0,
            "viewsMultiplier": 2.0,
            "usageCount": 3,
            "usageRate": 3.0,  # percent
        }
        fmt = {
            "format": "recipe",
            "avgViewsPerSubscriber": 2.0,
            "viewsMultiplier": 1.2,
            "count": 5,
            "usagePercent": 5.0,
        }
        content_gaps["keywordGaps"] = {"highValueKeywords": [keyword], "totalKeywords": 40}
        content_gaps["formatGaps"] = {"formatPerformance": [fmt], "recommendedFormats": [fmt]}

        result = _build_content_gap_insights(content_gaps, "2026-03-04T00:00:00Z")

        # Root-level fields the recommender reads (no nesting under 'contentGaps'),
        # plus keywordGaps/formatGaps passed through unchanged
        assert result == {
            "generatedAt": "2026-03-04T00:00:00Z",
            "totalVideos": 100,
            "totalTopics": 12,
            "avgViewsPerSubscriber": 1.5,
            "highOpportunity": [
                {"topic": "cooking/biryani", "avgViews": 5.0, "videoCount": 10, "opportunityScore": 2.5}
            ],
            "saturatedTopics": [{"topic": "cooking/general", "competition": "high"}],
            "keywordGaps": {"highValueKeywords": [keyword], "totalKeywords": 40},
            "formatGaps": {"formatPerformance": [fmt], "recommendedFormats": [fmt]},
        }

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

        assert set(result) == {"thumbnails", "titles", "timing", "contentGaps"}
        gaps_doc = result["contentGaps"]
        assert gaps_doc["highOpportunity"] == [
            {"topic": "test", "avgViews": 5.0, "videoCount": 10, "opportunityScore": 2.0}
        ]
        assert gaps_doc["saturatedTopics"] == [{"topic": "general", "competition": "high"}]
        # Missing sections in the report still produce the shape the recommender reads
        assert gaps_doc["keywordGaps"] == {"highValueKeywords": [], "totalKeywords": 0}
        assert gaps_doc["formatGaps"] == {"formatPerformance": [], "recommendedFormats": []}

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
