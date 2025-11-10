"""
Change detection and automated refresh system for Course Crusader.

Monitors university catalogs for updates and triggers re-scraping when changes are detected.
"""

import hashlib
import json
import requests
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class CatalogSnapshot:
    """
    Snapshot of a university catalog at a point in time.

    Used for change detection.
    """
    university: str
    url: str
    content_hash: str
    last_checked: str
    last_updated: str
    course_count: int
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'CatalogSnapshot':
        """Create from dictionary."""
        return cls(**data)


class ChangeDetector:
    """
    Detects changes in university course catalogs.

    Maintains snapshots and compares against current state.
    """

    def __init__(self, snapshot_file: str = "catalog_snapshots.json"):
        """
        Initialize change detector.

        Args:
            snapshot_file: Path to JSON file storing catalog snapshots
        """
        self.snapshot_file = Path(snapshot_file)
        self.snapshots: Dict[str, CatalogSnapshot] = {}
        self._load_snapshots()

    def _load_snapshots(self):
        """Load snapshots from file."""
        if self.snapshot_file.exists():
            with open(self.snapshot_file, 'r') as f:
                data = json.load(f)
                self.snapshots = {
                    k: CatalogSnapshot.from_dict(v)
                    for k, v in data.items()
                }

    def _save_snapshots(self):
        """Save snapshots to file."""
        data = {k: v.to_dict() for k, v in self.snapshots.items()}
        with open(self.snapshot_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _compute_content_hash(self, url: str) -> Optional[str]:
        """
        Compute hash of catalog content from URL.

        Args:
            url: URL to catalog page

        Returns:
            SHA256 hash of content, or None if fetch fails
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            content = response.content
            return hashlib.sha256(content).hexdigest()

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def check_for_changes(
        self,
        university: str,
        url: str,
        force: bool = False
    ) -> tuple[bool, str]:
        """
        Check if a catalog has changed since last snapshot.

        Args:
            university: University name
            url: Catalog URL
            force: Force update even if recent

        Returns:
            (has_changed, reason) tuple
        """
        current_hash = self._compute_content_hash(url)
        if current_hash is None:
            return False, "Failed to fetch catalog"

        if university not in self.snapshots:
            snapshot = CatalogSnapshot(
                university=university,
                url=url,
                content_hash=current_hash,
                last_checked=datetime.utcnow().isoformat(),
                last_updated=datetime.utcnow().isoformat(),
                course_count=0,
                notes="Initial snapshot"
            )
            self.snapshots[university] = snapshot
            self._save_snapshots()
            return True, "First snapshot - needs scraping"

        previous = self.snapshots[university]

        last_checked = datetime.fromisoformat(previous.last_checked)
        if not force and (datetime.utcnow() - last_checked) < timedelta(hours=1):
            return False, "Checked recently - skipping"

        previous.last_checked = datetime.utcnow().isoformat()

        if current_hash != previous.content_hash:
            previous.content_hash = current_hash
            previous.last_updated = datetime.utcnow().isoformat()
            previous.notes = "Catalog updated"
            self._save_snapshots()
            return True, "Catalog content changed"

        self._save_snapshots()
        return False, "No changes detected"

    def update_snapshot(
        self,
        university: str,
        course_count: int,
        notes: str = ""
    ):
        """
        Update snapshot after successful scrape.

        Args:
            university: University name
            course_count: Number of courses scraped
            notes: Additional notes
        """
        if university in self.snapshots:
            snapshot = self.snapshots[university]
            snapshot.course_count = course_count
            if notes:
                snapshot.notes = notes
            self._save_snapshots()

    def get_snapshot(self, university: str) -> Optional[CatalogSnapshot]:
        """Get snapshot for a university."""
        return self.snapshots.get(university)

    def list_all(self) -> List[CatalogSnapshot]:
        """List all snapshots."""
        return list(self.snapshots.values())

    def get_stale_catalogs(self, days: int = 7) -> List[str]:
        """
        Get list of catalogs not updated in X days.

        Args:
            days: Number of days threshold

        Returns:
            List of university names
        """
        threshold = datetime.utcnow() - timedelta(days=days)
        stale = []

        for name, snapshot in self.snapshots.items():
            last_updated = datetime.fromisoformat(snapshot.last_updated)
            if last_updated < threshold:
                stale.append(name)

        return stale


class RefreshScheduler:
    """
    Automated refresh scheduler for university catalogs.

    Manages periodic scraping and updates.
    """

    def __init__(
        self,
        change_detector: Optional[ChangeDetector] = None,
        check_interval_hours: int = 24
    ):
        """
        Initialize refresh scheduler.

        Args:
            change_detector: ChangeDetector instance (creates new if None)
            check_interval_hours: How often to check for changes
        """
        self.detector = change_detector or ChangeDetector()
        self.check_interval = timedelta(hours=check_interval_hours)

    def should_refresh(self, university: str, url: str) -> tuple[bool, str]:
        """
        Determine if a university catalog should be refreshed.

        Args:
            university: University name
            url: Catalog URL

        Returns:
            (should_refresh, reason) tuple
        """
        snapshot = self.detector.get_snapshot(university)

        if snapshot is None:
            return True, "Never scraped before"

        last_updated = datetime.fromisoformat(snapshot.last_updated)
        age = datetime.utcnow() - last_updated

        if age > timedelta(days=30):
            return True, f"Stale data (last updated {age.days} days ago)"

        has_changed, reason = self.detector.check_for_changes(university, url)
        return has_changed, reason

    def get_refresh_priority(self) -> List[tuple[str, int]]:
        """
        Get list of universities in priority order for refreshing.

        Returns:
            List of (university, priority_score) tuples, sorted by priority
        """
        priorities = []

        for snapshot in self.detector.list_all():
            last_updated = datetime.fromisoformat(snapshot.last_updated)
            days_old = (datetime.utcnow() - last_updated).days

            score = days_old

            priorities.append((snapshot.university, score))

        priorities.sort(key=lambda x: x[1], reverse=True)

        return priorities

    def generate_refresh_plan(
        self,
        max_universities: int = 5
    ) -> List[Dict]:
        """
        Generate a refresh plan for top priority universities.

        Args:
            max_universities: Maximum number of universities to include

        Returns:
            List of refresh task dictionaries
        """
        priorities = self.get_refresh_priority()[:max_universities]

        tasks = []
        for university, priority in priorities:
            snapshot = self.detector.get_snapshot(university)
            if snapshot:
                tasks.append({
                    'university': university,
                    'url': snapshot.url,
                    'priority': priority,
                    'last_updated': snapshot.last_updated,
                    'course_count': snapshot.course_count
                })

        return tasks
