"""Generate reports from insights analysis."""

import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from .config import config
from .firebase_client import save_insights


class ReportGenerator:
    """Generate and save insight reports."""

    def __init__(self):
        """Initialize report generator."""
        # Use timezone-aware UTC datetime (datetime.utcnow() is deprecated in Python 3.12+)
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def generate_thumbnail_report(self, patterns: Dict[str, Any],
                                 correlations: list) -> Dict[str, Any]:
        """Generate thumbnail insights report."""
        report = {
            'generatedAt': self.timestamp,
            'reportType': 'thumbnails',
            'patterns': patterns,
            'topCorrelations': correlations[:20],
        }

        # Extract top performing elements
        top_elements = []

        for category, data in patterns.items():
            if isinstance(data, dict) and 'topPatterns' in data:
                for pattern in data['topPatterns'][:3]:
                    top_elements.append({
                        'category': category,
                        'element': pattern['pattern'],
                        'lift': pattern['lift'],
                    })

        top_elements.sort(key=lambda x: x['lift'], reverse=True)
        report['topPerformingElements'] = top_elements[:10]

        return report

    def generate_title_report(self, patterns: Dict[str, Any],
                             correlations: list) -> Dict[str, Any]:
        """Generate title insights report."""
        report = {
            'generatedAt': self.timestamp,
            'reportType': 'titles',
            'patterns': patterns,
            'topCorrelations': correlations[:20],
            'topPowerWords': patterns.get('topPowerWords', []),
        }

        return report

    def generate_timing_report(self, timing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate timing insights report."""
        report = {
            'generatedAt': self.timestamp,
            'reportType': 'timing',
            'bestTimes': timing_data,
        }

        return report

    def generate_gap_report(self, content_gaps: Dict[str, Any],
                           keyword_gaps: Dict[str, Any],
                           format_gaps: Dict[str, Any]) -> Dict[str, Any]:
        """Generate content gap insights report."""
        report = {
            'generatedAt': self.timestamp,
            'reportType': 'contentGaps',
            'contentGaps': content_gaps,
            'keywordGaps': keyword_gaps,
            'formatGaps': format_gaps,
        }

        return report

    def save_to_firestore(self, report_type: str, report: Dict[str, Any]) -> None:
        """Save report to Firestore."""
        save_insights(report_type, report)
        print(f"Saved {report_type} insights to Firestore")

    def save_to_file(self, report_type: str, report: Dict[str, Any]) -> Path:
        """Save report to local JSON file."""
        # Use UTC timestamp for consistency with Firestore records
        filename = f"{report_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        filepath = config.OUTPUTS_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"Saved {report_type} report to {filepath}")
        return filepath

    def save_all(self, reports: Dict[str, Dict[str, Any]]) -> None:
        """Save all reports to both Firestore and local files."""
        for report_type, report in reports.items():
            self.save_to_firestore(report_type, report)
            self.save_to_file(report_type, report)
