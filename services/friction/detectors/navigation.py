# services/friction/detectors/navigation.py

import json
from datetime import datetime
from models.customer_journey import FrictionType

def detect_navigation_issues(
    raw_events,
    short_dwell_threshold: int = 5,     # seconds
    long_dwell_threshold: int = 120     # seconds (2 min)
):
    """
    Detect navigation frictions:
      - Back-and-forth (X→Y→X oscillation)
      - Short dwell (user leaves page very quickly, like a bounce)
      - Long dwell (user stays too long, possible stall)

    Args:
        raw_events: list of RawEvent (must have session_id, pathname, timestamp, event_name)
        short_dwell_threshold: dwell <= this = bounce
        long_dwell_threshold: dwell >= this = stall

    Returns:
        List[dict] friction points
    """
    friction_points = []

    # --- Group events per session ---
    sessions = {}
    for e in raw_events:
        if not e.session_id or not e.pathname:
            continue
        sessions.setdefault(e.session_id, []).append(e)

    # --- For each session ---
    for sid, evts in sessions.items():
        # Sort chronologically
        evts.sort(key=lambda x: x.timestamp)

        # --- Build navigation trail: pathname changes only ---
        nav_trail = []
        prev_path = None
        for e in evts:
            if e.pathname != prev_path:
                nav_trail.append((e, e.pathname))
                prev_path = e.pathname

        # --- Calculate dwell times & detect frictions ---
        visited = []
        for i, (e, path) in enumerate(nav_trail):
            # dwell = time until next distinct path
            if i + 1 < len(nav_trail):
                dwell = (nav_trail[i+1][0].timestamp - e.timestamp).total_seconds()
            else:
                dwell = None  # last page, unknown exit dwell

            # 1. Back-and-forth detection: X → Y → X
            if len(visited) >= 2 and path == visited[-2]:
                from_page = visited[-2]
                to_page = visited[-1]
                back_page = path
                friction_points.append({
                    "id": e.id,
                    "account_id": e.account_id,
                    "session_id": sid,
                    "event_name": "NAV_BACKTRACK",
                    "url": path,
                    "event_details": json.dumps({
                        "why": "Back-and-forth navigation detected",
                        "from": from_page,
                        "to": to_page,
                        "back": back_page,
                        "dwellSec": dwell
                    }),
                    "friction_type": FrictionType.BACKTRACKING,
                    "volume": 1,
                    "user_dismissed": False
                })

            # 2. Short dwell detection (bounce-like)
            if dwell is not None and dwell <= short_dwell_threshold:
                friction_points.append({
                    "id": e.id,
                    "account_id": e.account_id,
                    "session_id": sid,
                    "event_name": "NAV_BOUNCE",
                    "url": path,
                    "event_details": json.dumps({
                        "why": f"Users spend very little time ({dwell:.1f}s) on {path}",
                        "dwellSec": dwell
                    }),
                    "friction_type": FrictionType.BACKTRACKING,
                    "volume": 1,
                    "user_dismissed": False
                })

            # 3. Long dwell detection (stall)
            if dwell is not None and dwell >= long_dwell_threshold:
                friction_points.append({
                    "id": e.id,
                    "account_id": e.account_id,
                    "session_id": sid,
                    "event_name": "NAV_STALL",
                    "url": path,
                    "event_details": json.dumps({
                        "why": f"Users spend too long ({dwell:.1f}s) on {path}, may be stuck",
                        "dwellSec": dwell
                    }),
                    "friction_type": FrictionType.DELAY,
                    "volume": 1,
                    "user_dismissed": False
                })

            visited.append(path)

    return friction_points
