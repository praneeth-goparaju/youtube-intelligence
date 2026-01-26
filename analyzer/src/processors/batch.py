"""Batch processing for analysis jobs."""

import sys
import os
import time
from typing import Dict, Any, List, Optional, Callable
from tqdm import tqdm

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from shared.constants import ANALYSIS_TYPES

from ..firebase_client import get_all_channels, get_channel_videos, get_unanalyzed_videos
from ..analyzers import ThumbnailAnalyzer, TitleAnalyzer, DescriptionAnalyzer, TagsAnalyzer, ContentStructureAnalyzer
from ..config import config, logger
from .progress import ProgressTracker


# Default limit when no limit specified (effectively unlimited for practical purposes)
DEFAULT_VIDEO_LIMIT = 10000


class BatchProcessor:
    """Process videos in batches for analysis."""

    def __init__(self, analysis_type: str):
        """
        Initialize batch processor.

        Args:
            analysis_type: Type of analysis (thumbnail, title, description, tags)
        """
        self.analysis_type = analysis_type
        self.progress = ProgressTracker(analysis_type)

        # Initialize appropriate analyzer
        analyzers = {
            'thumbnail': ThumbnailAnalyzer(),
            'title': TitleAnalyzer(),
            'description': DescriptionAnalyzer(),
            'tags': TagsAnalyzer(),
            'content_structure': ContentStructureAnalyzer(),
        }

        if analysis_type not in analyzers:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

        self.analyzer = analyzers[analysis_type]

    def process_all_channels(self, limit: Optional[int] = None,
                            channel_filter: Optional[Callable[[Dict], bool]] = None) -> Dict[str, Any]:
        """
        Process all channels.

        Args:
            limit: Maximum number of videos to process per channel (None = all)
            channel_filter: Optional filter function for channels

        Returns:
            Processing statistics
        """
        channels = get_all_channels()

        if channel_filter:
            channels = [c for c in channels if channel_filter(c)]

        print(f"\n{'='*60}")
        print(f"  {self.analysis_type.upper()} ANALYSIS")
        print(f"  Processing {len(channels)} channels")
        print(f"{'='*60}\n")

        total_processed = 0
        total_successful = 0
        total_failed = 0
        total_skipped = 0

        for channel in channels:
            channel_id = channel['id']
            channel_title = channel.get('channelTitle', channel_id)

            print(f"\nChannel: {channel_title}")
            print(f"-" * 40)

            stats = self.process_channel(channel_id, limit=limit)

            total_processed += stats['processed']
            total_successful += stats['successful']
            total_failed += stats['failed']
            total_skipped += stats['skipped']

        return {
            'channels': len(channels),
            'processed': total_processed,
            'successful': total_successful,
            'failed': total_failed,
            'skipped': total_skipped,
        }

    def process_channel(self, channel_id: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Process all videos in a channel.

        Args:
            channel_id: The channel ID to process
            limit: Maximum number of videos to process (None = all)

        Returns:
            Processing statistics
        """
        # Get unanalyzed videos with the specified limit
        # The limit is passed directly to get_unanalyzed_videos which handles the filtering
        effective_limit = limit or DEFAULT_VIDEO_LIMIT
        videos = get_unanalyzed_videos(channel_id, self.analysis_type, effective_limit)

        if not videos:
            print(f"  No unanalyzed videos found")
            return {'processed': 0, 'successful': 0, 'failed': 0, 'skipped': 0}

        self.progress.start(len(videos))

        for video in tqdm(videos, desc=f"  Analyzing {self.analysis_type}s"):
            video_id = video['id']

            try:
                result = self._analyze_video(channel_id, video)

                if result is None:
                    self.progress.record_skip()
                else:
                    self.progress.record_success()

            except Exception as e:
                logger.error(f"Error processing {video_id}: {e}")
                self.progress.record_failure()

            # Rate limiting
            time.sleep(config.REQUEST_DELAY)

        stats = self.progress.get_stats()
        print(f"  Completed: {stats['successful']} success, {stats['failed']} failed, {stats['skipped']} skipped")

        return {
            'processed': stats['processed'],
            'successful': stats['successful'],
            'failed': stats['failed'],
            'skipped': stats['skipped'],
        }

    def _analyze_video(self, channel_id: str, video: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze a single video.

        Args:
            channel_id: The channel ID
            video: Video data dictionary

        Returns:
            Analysis result or None if skipped/failed
        """
        video_id = video['id']

        if self.analysis_type == 'thumbnail':
            thumbnail_path = video.get('thumbnailStoragePath', '')
            if not thumbnail_path:
                # Try to construct from video ID
                thumbnails = video.get('thumbnails', {})
                thumbnail_url = thumbnails.get('medium', thumbnails.get('default', ''))
                if thumbnail_url:
                    return self.analyzer.analyze_from_url(channel_id, video_id, thumbnail_url)
                return None
            return self.analyzer.analyze(channel_id, video_id, thumbnail_path)

        elif self.analysis_type == 'title':
            title = video.get('title', '')
            return self.analyzer.analyze(channel_id, video_id, title)

        elif self.analysis_type == 'description':
            description = video.get('description', '')
            return self.analyzer.analyze(channel_id, video_id, description)

        elif self.analysis_type == 'tags':
            tags = video.get('tags', [])
            return self.analyzer.analyze(channel_id, video_id, tags)

        elif self.analysis_type == 'content_structure':
            title = video.get('title', '')
            description = video.get('description', '')
            duration_seconds = video.get('durationSeconds', 0)
            tags = video.get('tags', [])
            return self.analyzer.analyze(
                channel_id, video_id, title, description, duration_seconds, tags
            )

        return None


def run_all_analysis(limit_per_channel: Optional[int] = None) -> Dict[str, Any]:
    """
    Run all analysis types on all channels.

    Args:
        limit_per_channel: Maximum videos per channel per analysis type

    Returns:
        Combined statistics
    """
    results = {}

    for analysis_type in ANALYSIS_TYPES:
        print(f"\n\n{'#'*60}")
        print(f"  STARTING {analysis_type.upper()} ANALYSIS")
        print(f"{'#'*60}")

        processor = BatchProcessor(analysis_type)
        results[analysis_type] = processor.process_all_channels(limit=limit_per_channel)

    # Print summary
    print(f"\n\n{'='*60}")
    print("  ANALYSIS COMPLETE - SUMMARY")
    print(f"{'='*60}")

    for analysis_type, stats in results.items():
        print(f"\n{analysis_type.upper()}:")
        print(f"  Channels: {stats['channels']}")
        print(f"  Processed: {stats['processed']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped: {stats['skipped']}")

    return results
