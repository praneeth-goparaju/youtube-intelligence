"""Content gap analysis to find underserved topics and keywords.

Uses viewsPerSubscriber as the performance metric to normalize across
channels of different sizes.
"""

from typing import Dict, Any, List, Callable
from collections import defaultdict
import numpy as np


# Configuration constants
MIN_VIDEOS_FOR_TOPIC = 3
MIN_VIDEOS_FOR_KEYWORD = 2
SATURATION_THRESHOLD = 0.1  # Topics with >10% of videos are saturated
KEYWORD_OPPORTUNITY_THRESHOLD = 0.1  # Keywords in <10% of videos


class GapAnalyzer:
    """Analyze content gaps and opportunities."""

    def __init__(self, videos: List[Dict[str, Any]],
                 get_vps: Callable[[Dict], float]):
        """
        Initialize analyzer.

        Args:
            videos: List of video data dicts (with title_analysis, channel, etc.)
            get_vps: Function to extract viewsPerSubscriber from a video dict.
        """
        self.videos = videos
        self.get_vps = get_vps

    def find_content_gaps(self) -> Dict[str, Any]:
        """Find underserved content areas with high potential."""
        topic_performance = defaultdict(list)

        for video in self.videos:
            analysis = video.get('title_analysis', {})
            keywords = analysis.get('keywords', {})

            niche = keywords.get('niche', 'unknown')
            sub_niche = keywords.get('subNiche', '')
            topic = f"{niche}/{sub_niche}" if sub_niche else niche

            vps = self.get_vps(video)
            if vps > 0:
                topic_performance[topic].append(vps)

        opportunities = []
        total_videos = len(self.videos)

        for topic, vps_list in topic_performance.items():
            if len(vps_list) < MIN_VIDEOS_FOR_TOPIC:
                continue

            avg_vps = float(np.mean(vps_list))
            video_count = len(vps_list)
            share = video_count / total_videos if total_videos > 0 else 0

            # High opportunity: high viewsPerSub, low competition
            opportunity_score = avg_vps / (video_count + 1)

            opportunities.append({
                'topic': topic,
                'avgViewsPerSubscriber': round(avg_vps, 2),
                'videoCount': video_count,
                'contentShare': round(share * 100, 2),
                'opportunityScore': round(opportunity_score, 3),
            })

        opportunities.sort(key=lambda x: x['opportunityScore'], reverse=True)

        all_vps = [self.get_vps(v) for v in self.videos if self.get_vps(v) > 0]
        avg_all = float(np.mean(all_vps)) if all_vps else 0

        saturated = [
            opp for opp in opportunities
            if opp['videoCount'] > total_videos * SATURATION_THRESHOLD
            and opp['avgViewsPerSubscriber'] < avg_all * 0.8
        ]

        return {
            'highOpportunity': opportunities[:20],
            'saturatedTopics': saturated[:10],
            'totalTopics': len(opportunities),
            'avgViewsPerSubscriber': round(avg_all, 2),
        }

    def analyze_keyword_gaps(self) -> Dict[str, Any]:
        """Find high-performing keywords with low usage."""
        keyword_performance = defaultdict(list)

        for video in self.videos:
            analysis = video.get('title_analysis', {})
            keywords = analysis.get('keywords', {})
            vps = self.get_vps(video)

            if vps <= 0:
                continue

            primary = keywords.get('primaryKeyword', '')
            if primary:
                keyword_performance[primary.lower()].append(vps)

            for kw in keywords.get('secondaryKeywords', []):
                if kw:
                    keyword_performance[kw.lower()].append(vps)

        opportunities = []
        total_videos = len(self.videos)
        all_vps = [self.get_vps(v) for v in self.videos if self.get_vps(v) > 0]
        avg_vps = float(np.mean(all_vps)) if all_vps else 0

        for keyword, vps_list in keyword_performance.items():
            if len(vps_list) < MIN_VIDEOS_FOR_KEYWORD:
                continue

            kw_avg = float(np.mean(vps_list))
            count = len(vps_list)
            usage_rate = count / total_videos if total_videos > 0 else 0

            if kw_avg > avg_vps and usage_rate < KEYWORD_OPPORTUNITY_THRESHOLD:
                opportunities.append({
                    'keyword': keyword,
                    'avgViewsPerSubscriber': round(kw_avg, 2),
                    'viewsMultiplier': round(kw_avg / avg_vps, 2) if avg_vps > 0 else 1.0,
                    'usageCount': count,
                    'usageRate': round(usage_rate * 100, 2),
                })

        opportunities.sort(key=lambda x: x['viewsMultiplier'], reverse=True)

        return {
            'highValueKeywords': opportunities[:30],
            'totalKeywords': len(keyword_performance),
        }

    def analyze_format_gaps(self) -> Dict[str, Any]:
        """Find underused content formats with high potential."""
        format_performance = defaultdict(list)

        for video in self.videos:
            analysis = video.get('title_analysis', {})
            content_signals = analysis.get('contentSignals', {})
            vps = self.get_vps(video)

            if vps <= 0:
                continue

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
                    format_performance[format_name].append(vps)

        results = []
        all_vps = [self.get_vps(v) for v in self.videos if self.get_vps(v) > 0]
        avg_vps = float(np.mean(all_vps)) if all_vps else 0
        total_videos = len(self.videos)

        for format_name, vps_list in format_performance.items():
            if not vps_list:
                continue

            fmt_avg = float(np.mean(vps_list))
            count = len(vps_list)
            usage = count / total_videos if total_videos > 0 else 0

            results.append({
                'format': format_name,
                'avgViewsPerSubscriber': round(fmt_avg, 2),
                'viewsMultiplier': round(fmt_avg / avg_vps, 2) if avg_vps > 0 else 1.0,
                'count': count,
                'usagePercent': round(usage * 100, 2),
            })

        results.sort(key=lambda x: x['viewsMultiplier'], reverse=True)

        return {
            'formatPerformance': results,
            'recommendedFormats': [r for r in results if r['viewsMultiplier'] > 1.0],
        }
