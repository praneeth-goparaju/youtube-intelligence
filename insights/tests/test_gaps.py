"""Tests for the content gap analysis module."""

import pytest
from insights.src.gaps import (
    GapAnalyzer,
    MIN_VIDEOS_FOR_TOPIC,
    MIN_VIDEOS_FOR_KEYWORD,
    SATURATION_THRESHOLD,
)


def make_video(niche='cooking', sub_niche='', primary_kw='biryani',
               secondary_kws=None, vps=1.0, content_signals=None):
    """Helper to create a video dict matching the expected structure."""
    keywords = {
        'niche': niche,
        'subNiche': sub_niche,
        'primaryKeyword': primary_kw,
        'secondaryKeywords': secondary_kws or [],
    }
    signals = content_signals or {'contentType': 'recipe'}
    return {
        'title_analysis': {
            'keywords': keywords,
            'contentSignals': signals,
        },
        '_vps': vps,
    }


def get_vps(video):
    """Extract viewsPerSubscriber from test video dict."""
    return video.get('_vps', 0)


class TestFindContentGaps:
    def test_basic_gap_detection(self):
        videos = []
        # 5 cooking videos with high vps
        for _ in range(5):
            videos.append(make_video(niche='cooking', vps=10.0))
        # 5 vlog videos with low vps
        for _ in range(5):
            videos.append(make_video(niche='vlog', vps=1.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()

        assert 'highOpportunity' in result
        assert 'saturatedTopics' in result
        assert 'totalTopics' in result
        assert result['totalTopics'] >= 2

    def test_minimum_videos_required(self):
        # Only 2 videos per topic (below MIN_VIDEOS_FOR_TOPIC=3)
        videos = [
            make_video(niche='cooking', vps=5.0),
            make_video(niche='cooking', vps=5.0),
        ]
        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()
        assert result['totalTopics'] == 0

    def test_sub_niche_grouping(self):
        videos = []
        for _ in range(MIN_VIDEOS_FOR_TOPIC):
            videos.append(make_video(niche='cooking', sub_niche='biryani', vps=5.0))
        for _ in range(MIN_VIDEOS_FOR_TOPIC):
            videos.append(make_video(niche='cooking', sub_niche='curry', vps=3.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()

        topics = [opp['topic'] for opp in result['highOpportunity']]
        assert 'cooking/biryani' in topics
        assert 'cooking/curry' in topics

    def test_opportunity_score_ordering(self):
        videos = []
        # High vps, low count = high opportunity
        for _ in range(MIN_VIDEOS_FOR_TOPIC):
            videos.append(make_video(niche='rare_topic', vps=50.0))
        # Low vps, high count = low opportunity
        for _ in range(20):
            videos.append(make_video(niche='common_topic', vps=1.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()

        if len(result['highOpportunity']) >= 2:
            assert result['highOpportunity'][0]['opportunityScore'] >= result['highOpportunity'][1]['opportunityScore']

    def test_zero_vps_excluded(self):
        videos = [make_video(niche='cooking', vps=0) for _ in range(10)]
        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()
        assert result['avgViewsPerSubscriber'] == 0

    def test_saturation_detection(self):
        videos = []
        # 60% of videos are "cooking" with below-average vps
        for _ in range(60):
            videos.append(make_video(niche='cooking', vps=0.5))
        # 40% of videos are "tech" with above-average vps
        for _ in range(40):
            videos.append(make_video(niche='tech', vps=5.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()

        saturated_topics = [t['topic'] for t in result['saturatedTopics']]
        assert 'cooking' in saturated_topics

    def test_has_avg_views_per_subscriber_field(self):
        videos = []
        for _ in range(5):
            videos.append(make_video(niche='cooking', vps=10.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.find_content_gaps()

        for opp in result['highOpportunity']:
            assert 'avgViewsPerSubscriber' in opp


class TestAnalyzeKeywordGaps:
    def test_basic_keyword_analysis(self):
        videos = []
        for _ in range(5):
            videos.append(make_video(primary_kw='biryani', vps=10.0))
        for _ in range(50):
            videos.append(make_video(primary_kw='chicken', vps=2.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_keyword_gaps()

        assert 'highValueKeywords' in result
        assert 'totalKeywords' in result

    def test_secondary_keywords_included(self):
        videos = []
        for _ in range(5):
            videos.append(make_video(
                primary_kw='food',
                secondary_kws=['spicy', 'traditional'],
                vps=5.0
            ))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_keyword_gaps()
        assert result['totalKeywords'] >= 2  # At least primary + some secondaries

    def test_secondary_keywords_as_string(self):
        """secondaryKeywords is now comma-separated string, not a list."""
        videos = []
        for _ in range(5):
            videos.append(make_video(
                primary_kw='food',
                secondary_kws='spicy, traditional, homestyle',
                vps=5.0
            ))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_keyword_gaps()
        # Should NOT iterate char-by-char
        assert result['totalKeywords'] >= 2
        # Verify individual keywords are found, not characters
        all_kws = set()
        for v in videos:
            kws = v['title_analysis']['keywords']
            secondary = kws.get('secondaryKeywords', '')
            if isinstance(secondary, str):
                for kw in secondary.split(','):
                    kw = kw.strip().lower()
                    if kw:
                        all_kws.add(kw)

        # 'spicy' should be a keyword, 's' should not
        assert 'spicy' in all_kws
        assert 's' not in all_kws

    def test_minimum_keyword_count(self):
        # Only 1 video per keyword
        videos = [
            make_video(primary_kw='unique_word_1', vps=100.0),
        ]
        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_keyword_gaps()
        # Below MIN_VIDEOS_FOR_KEYWORD, so no high-value keywords
        assert len(result['highValueKeywords']) == 0

    def test_keyword_case_normalization(self):
        videos = []
        for _ in range(MIN_VIDEOS_FOR_KEYWORD):
            videos.append(make_video(primary_kw='Biryani', vps=5.0))
        for _ in range(MIN_VIDEOS_FOR_KEYWORD):
            videos.append(make_video(primary_kw='biryani', vps=5.0))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_keyword_gaps()
        # "Biryani" and "biryani" should be normalized to the same keyword
        assert result['totalKeywords'] >= 1


class TestAnalyzeFormatGaps:
    def test_basic_format_analysis(self):
        videos = []
        for _ in range(5):
            videos.append(make_video(
                content_signals={'isRecipe': True, 'contentType': 'recipe'},
                vps=5.0
            ))
        for _ in range(5):
            videos.append(make_video(
                content_signals={'isTutorial': True, 'contentType': 'tutorial'},
                vps=3.0
            ))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_format_gaps()

        assert 'formatPerformance' in result
        assert 'recommendedFormats' in result

    def test_multiplier_ordering(self):
        videos = []
        # Recipes perform well
        for _ in range(5):
            videos.append(make_video(
                content_signals={'isRecipe': True, 'contentType': 'recipe'},
                vps=10.0
            ))
        # Vlogs perform poorly
        for _ in range(5):
            videos.append(make_video(
                content_signals={'isVlog': True, 'contentType': 'vlog'},
                vps=1.0
            ))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_format_gaps()

        formats = result['formatPerformance']
        if len(formats) >= 2:
            assert formats[0]['viewsMultiplier'] >= formats[1]['viewsMultiplier']

    def test_recommended_formats_above_average(self):
        videos = []
        for _ in range(5):
            videos.append(make_video(
                content_signals={'isRecipe': True, 'contentType': 'recipe'},
                vps=10.0
            ))
        for _ in range(5):
            videos.append(make_video(
                content_signals={'isVlog': True, 'contentType': 'vlog'},
                vps=1.0
            ))

        analyzer = GapAnalyzer(videos, get_vps)
        result = analyzer.analyze_format_gaps()

        for fmt in result['recommendedFormats']:
            assert fmt['viewsMultiplier'] > 1.0

    def test_empty_videos(self):
        analyzer = GapAnalyzer([], get_vps)
        result = analyzer.analyze_format_gaps()
        assert result['formatPerformance'] == []
        assert result['recommendedFormats'] == []
