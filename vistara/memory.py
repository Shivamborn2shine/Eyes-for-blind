"""
Assistive spatial memory for personal belongings.
Tracks what items were placed where (clock position, horizontal location, proximity depth)
and audits departure to prevent forgetting items.
"""
import json
import time
from pathlib import Path
from typing import Dict, Tuple, Optional, List


def to_clock(pos: str) -> Tuple[str, str]:
    """Map spatial position to English and Hindi clock direction."""
    if pos == "left":
        return "at 10 o'clock on your left", "10 बजे बाईं ओर"
    elif pos == "right":
        return "at 2 o'clock on your right", "2 बजे दाईं ओर"
    return "straight ahead in the center", "बिल्कुल सामने बीच में"


def to_proximity(prox: str) -> Tuple[str, str]:
    """Map proximity depth to natural English and Hindi phrases."""
    if prox == "close":
        return "close, right near your hands", "बिल्कुल पास में"
    elif prox == "far":
        return "further away towards the edge", "कुछ दूरी पर किनारे की तरफ़"
    return "at arm's length", "हाथ की दूरी पर"


class ItemMemory:
    """Manages spatial item memory, last-seen sightings, and departure audits."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot = {}       # {'bottle': 1}
        self.snapshot_pos = {}   # {'bottle': 'left'}
        self.snapshot_prox = {}  # {'bottle': 'medium'}
        self.snapshot_time = None
        self.last_seen = {}      # {'bottle': {'pos': 'left', 'prox': 'medium', 'clock': 'at 10...', 'time': 1700000000}}
        self._load()

    # ---------------------------------------------------------- persistence
    def _load(self):
        if self.path.exists():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                self.snapshot = d.get("snapshot", {})
                self.snapshot_pos = d.get("snapshot_pos", {})
                self.snapshot_prox = d.get("snapshot_prox", {})
                self.snapshot_time = d.get("snapshot_time")
                self.last_seen = d.get("last_seen", {})
            except Exception:
                pass

    def save(self):
        self.path.write_text(json.dumps({
            "snapshot": self.snapshot,
            "snapshot_pos": self.snapshot_pos,
            "snapshot_prox": self.snapshot_prox,
            "snapshot_time": self.snapshot_time,
            "last_seen": self.last_seen,
        }, indent=2), encoding="utf-8")

    # ---------------------------------------------------------- operations
    def remember(self, counts: Dict[str, int], positions: Dict[str, str], proximities: Optional[Dict[str, str]] = None):
        """Save a snapshot of items placed on the desk/table with spatial coordinates."""
        self.snapshot = dict(counts)
        self.snapshot_pos = dict(positions)
        self.snapshot_prox = dict(proximities or {})
        self.snapshot_time = time.time()
        self.update_seen(counts, positions, proximities)
        self.save()

    def update_seen(self, counts: Dict[str, int], positions: Dict[str, str], proximities: Optional[Dict[str, str]] = None):
        """Update last seen log with high-precision clock direction and proximity depth."""
        now = time.time()
        proximities = proximities or {}
        for name in counts:
            pos = positions.get(name, "center")
            prox = proximities.get(name, "medium")
            clock_en, clock_hi = to_clock(pos)
            prox_en, prox_hi = to_proximity(prox)
            self.last_seen[name] = {
                "pos": pos,
                "prox": prox,
                "clock_en": clock_en,
                "clock_hi": clock_hi,
                "prox_en": prox_en,
                "prox_hi": prox_hi,
                "time": now,
            }

    def find_item(self, query: str) -> Optional[Dict]:
        """Search memory for a specific item (e.g. 'phone', 'keys', 'bottle')."""
        query = query.strip().lower()
        if not query or not self.last_seen:
            return None

        # Check exact or partial match
        match_key = None
        for k in self.last_seen:
            if query == k.lower() or query in k.lower() or k.lower() in query:
                match_key = k
                break

        if not match_key:
            return None

        item = self.last_seen[match_key]
        now = time.time()
        secs_ago = max(0, int(now - item.get("time", now)))
        mins_ago = secs_ago // 60

        return {
            "name": match_key,
            "pos": item.get("pos", "center"),
            "prox": item.get("prox", "medium"),
            "clock_en": item.get("clock_en", to_clock(item.get("pos", "center"))[0]),
            "clock_hi": item.get("clock_hi", to_clock(item.get("pos", "center"))[1]),
            "prox_en": item.get("prox_en", to_proximity(item.get("prox", "medium"))[0]),
            "prox_hi": item.get("prox_hi", to_proximity(item.get("prox", "medium"))[1]),
            "seconds_ago": secs_ago,
            "minutes_ago": mins_ago,
            "time": item.get("time", now),
        }

    def leaving_audit(self, counts_now: Dict[str, int], positions_now: Dict[str, str], proximities_now: Optional[Dict[str, str]] = None):
        """
        Comprehensive audit comparing snapshot to current table state.
        Returns:
          left_items: {'bottle': 1, ...}
          picked_up: ['laptop', 'cell phone', ...]
          positions: {'bottle': 'left'}
          proximities: {'bottle': 'close'}
        """
        left, picked_up, pos, prox = {}, [], {}, {}
        proximities_now = proximities_now or {}

        for name, orig_count in self.snapshot.items():
            now_count = counts_now.get(name, 0)
            if now_count > 0:
                left[name] = min(orig_count, now_count)
                pos[name] = positions_now.get(name, self.snapshot_pos.get(name, "center"))
                prox[name] = proximities_now.get(name, self.snapshot_prox.get(name, "medium"))
            else:
                picked_up.append(name)

        return left, picked_up, pos, prox

    def left_behind(self, counts_now, positions_now, proximities_now=None):
        """Backward compatible check for forgotten items."""
        left, _, pos, _ = self.leaving_audit(counts_now, positions_now, proximities_now)
        return left, pos

    def clear_snapshot(self):
        self.snapshot, self.snapshot_pos, self.snapshot_prox, self.snapshot_time = {}, {}, {}, None
        self.save()

    def has_snapshot(self):
        return bool(self.snapshot)
