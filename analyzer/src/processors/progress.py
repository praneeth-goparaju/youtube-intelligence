"""Progress tracking for analysis jobs."""

from typing import Dict, Any, Optional
from datetime import datetime

from ..firebase_client import save_analysis_progress, get_analysis_progress


class ProgressTracker:
    """Track progress of analysis jobs."""

    def __init__(self, analysis_type: str):
        """
        Initialize progress tracker.

        Args:
            analysis_type: Type of analysis (thumbnail, title, description, tags)
        """
        self.analysis_type = analysis_type
        self.start_time: Optional[datetime] = None
        self.total_videos: int = 0
        self.processed: int = 0
        self.successful: int = 0
        self.failed: int = 0
        self.skipped: int = 0

    def start(self, total_videos: int) -> None:
        """Start tracking a new job."""
        self.start_time = datetime.utcnow()
        self.total_videos = total_videos
        self.processed = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self._save()

    def record_success(self) -> None:
        """Record a successful analysis."""
        self.processed += 1
        self.successful += 1
        self._save()

    def record_failure(self) -> None:
        """Record a failed analysis."""
        self.processed += 1
        self.failed += 1
        self._save()

    def record_skip(self) -> None:
        """Record a skipped analysis (already exists)."""
        self.processed += 1
        self.skipped += 1
        self._save()

    def force_save(self) -> None:
        """Force immediate save (call at end of batch)."""
        self._save(force=True)

    def get_progress(self) -> float:
        """Get progress as percentage."""
        if self.total_videos == 0:
            return 0.0
        return (self.processed / self.total_videos) * 100

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        elapsed = None
        if self.start_time:
            elapsed = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            'analysisType': self.analysis_type,
            'totalVideos': self.total_videos,
            'processed': self.processed,
            'successful': self.successful,
            'failed': self.failed,
            'skipped': self.skipped,
            'progress': self.get_progress(),
            'elapsedSeconds': elapsed,
            'startTime': self.start_time.isoformat() if self.start_time else None,
        }

    def _save(self, force: bool = False) -> None:
        """Save progress to Firestore (batched writes for efficiency)."""
        # Only write every 10 records to reduce Firestore quota usage, or on force
        if force or self.processed % 10 == 0:
            save_analysis_progress(self.analysis_type, self.get_stats())

    def load(self) -> bool:
        """
        Load existing progress from Firestore.

        Returns:
            True if progress was loaded, False if no existing progress
        """
        data = get_analysis_progress(self.analysis_type)
        if data:
            self.total_videos = data.get('totalVideos', 0)
            self.processed = data.get('processed', 0)
            self.successful = data.get('successful', 0)
            self.failed = data.get('failed', 0)
            self.skipped = data.get('skipped', 0)
            if data.get('startTime'):
                self.start_time = datetime.fromisoformat(data['startTime'])
            return True
        return False

    def print_status(self) -> None:
        """Print current status to console."""
        stats = self.get_stats()
        print(f"\n{'='*60}")
        print(f"Analysis: {stats['analysisType'].upper()}")
        print(f"{'='*60}")
        print(f"Progress: {stats['progress']:.1f}% ({stats['processed']}/{stats['totalVideos']})")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Skipped: {stats['skipped']}")
        if stats['elapsedSeconds']:
            minutes = int(stats['elapsedSeconds'] // 60)
            seconds = int(stats['elapsedSeconds'] % 60)
            print(f"Elapsed: {minutes}m {seconds}s")
        print(f"{'='*60}\n")
