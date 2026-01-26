"""Content gap analysis to find underserved topics."""

from typing import Dict, Any, List
from collections import Counter, defaultdict
import numpy as np


# Configuration constants for gap analysis
MIN_VIDEOS_FOR_TOPIC = 3  # Minimum videos required to analyze a topic
MIN_VIDEOS_FOR_KEYWORD = 2  # Minimum videos for keyword analysis
SATURATION_THRESHOLD = 0.1  # Topics with >10% of videos are considered saturated
UNDERPERFORMING_THRESHOLD = 0.8  # Topics with <80% of average views are underperforming
KEYWORD_OPPORTUNITY_THRESHOLD = 0.1  # Keywords used in <10% of videos may be opportunities


class GapAnalyzer:
    """Analyze content gaps and opportunities."""

    def __init__(self, videos_with_analysis: List[Dict[str, Any]]):
        """
        Initialize analyzer.

        Args:
            videos_with_analysis: List of videos with analysis data
        """
        self.videos = videos_with_analysis

    def find_content_gaps(self) -> Dict[str, Any]:
        """Find underserved content areas with high potential."""
        # Analyze by niche/topic
        topic_performance = defaultdict(list)

        for video in self.videos:
            analysis = video.get('analysis', {})
            keywords = analysis.get('keywords', {})

            niche = keywords.get('niche', 'unknown')
            sub_niche = keywords.get('subNiche', '')

            topic = f"{niche}/{sub_niche}" if sub_niche else niche
            views = video['video'].get('viewCount', 0)

            topic_performance[topic].append(views)

        # Calculate opportunity scores
        opportunities = []
        total_videos = len(self.videos)

        for topic, views in topic_performance.items():
            if len(views) < MIN_VIDEOS_FOR_TOPIC:
                continue

            avg_views = np.mean(views)
            video_count = len(views)
            share = video_count / total_videos if total_videos > 0 else 0

            # High opportunity: high views, low competition
            # Score = avg_views / (video_count + 1)
            opportunity_score = avg_views / (video_count + 1)

            opportunities.append({
                'topic': topic,
                'avgViews': int(avg_views),
                'videoCount': video_count,
                'contentShare': round(share * 100, 2),
                'opportunityScore': round(opportunity_score),
            })

        # Sort by opportunity score
        opportunities.sort(key=lambda x: x['opportunityScore'], reverse=True)

        # Find saturated topics (many videos, average performance)
        all_views = [v['video'].get('viewCount', 0) for v in self.videos]
        avg_all_views = np.mean(all_views) if all_views else 0
        saturated = [
            opp for opp in opportunities
            if opp['videoCount'] > len(self.videos) * SATURATION_THRESHOLD
            and opp['avgViews'] < avg_all_views * UNDERPERFORMING_THRESHOLD
        ]

        return {
            'highOpportunity': opportunities[:20],
            'saturatedTopics': saturated[:10],
            'totalTopics': len(opportunities),
            'avgViewsAcrossAll': int(avg_all_views) if avg_all_views else 0,
        }

    def analyze_keyword_gaps(self) -> Dict[str, Any]:
        """Find high-performing keywords with low usage."""
        keyword_performance = defaultdict(list)

        for video in self.videos:
            analysis = video.get('analysis', {})
            keywords = analysis.get('keywords', {})
            views = video['video'].get('viewCount', 0)

            # Primary keyword
            primary = keywords.get('primaryKeyword', '')
            if primary:
                keyword_performance[primary.lower()].append(views)

            # Secondary keywords
            for kw in keywords.get('secondaryKeywords', []):
                if kw:
                    keyword_performance[kw.lower()].append(views)

        # Find high-performing but underused keywords
        opportunities = []
        total_videos = len(self.videos)
        all_views = [v['video'].get('viewCount', 0) for v in self.videos]
        avg_views = np.mean(all_views) if all_views else 0

        for keyword, views in keyword_performance.items():
            if len(views) < MIN_VIDEOS_FOR_KEYWORD:
                continue

            kw_avg = np.mean(views)
            count = len(views)
            usage_rate = count / total_videos if total_videos > 0 else 0

            # High opportunity: high performance, low usage
            if kw_avg > avg_views and usage_rate < KEYWORD_OPPORTUNITY_THRESHOLD:
                opportunities.append({
                    'keyword': keyword,
                    'avgViews': int(kw_avg),
                    'viewMultiplier': round(kw_avg / avg_views, 2) if avg_views > 0 else 1.0,
                    'usageCount': count,
                    'usageRate': round(usage_rate * 100, 2),
                })

        opportunities.sort(key=lambda x: x['viewMultiplier'], reverse=True)

        return {
            'highValueKeywords': opportunities[:30],
            'totalKeywords': len(keyword_performance),
        }

    def analyze_format_gaps(self) -> Dict[str, Any]:
        """Find underused content formats with high potential."""
        format_performance = defaultdict(list)

        for video in self.videos:
            analysis = video.get('analysis', {})
            content_signals = analysis.get('contentSignals', {})
            views = video['video'].get('viewCount', 0)

            # Check each format type
            formats = [
                ('recipe', content_signals.get('isRecipe', False)),
                ('tutorial', content_signals.get('isTutorial', False)),
                ('review', content_signals.get('isReview', False)),
                ('vlog', content_signals.get('isVlog', False)),
                ('challenge', content_signals.get('isChallenge', False)),
                ('reaction', content_signals.get('isReaction', False)),
                ('comparison', content_signals.get('isComparison', False)),
                ('list', content_signals.get('isList', False)),
                ('storytime', content_signals.get('isStorytime', False)),
            ]

            for format_name, is_format in formats:
                if is_format:
                    format_performance[format_name].append(views)

        # Analyze each format
        results = []
        total_videos = len(self.videos)
        all_views = [v['video'].get('viewCount', 0) for v in self.videos]
        avg_views = np.mean(all_views) if all_views else 0

        for format_name, views in format_performance.items():
            if not views:
                continue

            fmt_avg = np.mean(views)
            count = len(views)
            usage = count / total_videos if total_videos > 0 else 0

            results.append({
                'format': format_name,
                'avgViews': int(fmt_avg),
                'viewMultiplier': round(fmt_avg / avg_views, 2) if avg_views > 0 else 1.0,
                'count': count,
                'usagePercent': round(usage * 100, 2),
            })

        results.sort(key=lambda x: x['viewMultiplier'], reverse=True)

        return {
            'formatPerformance': results,
            'recommendedFormats': [r for r in results if r['viewMultiplier'] > 1.0],
        }
