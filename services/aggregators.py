# services/aggregators.py
from sqlalchemy.orm import Session
from models import EventsUsage, FormUsage, JourneyFriction, PageUsage

from sqlalchemy.orm import Session
from sqlalchemy import func, text, desc
from db import db
import math
from utils.url_utils import make_pretty_url

def get_page_usage(account_id: int, limit: int = 20):
    """
    Fetch page usage stats for an account, ordered by total visits (desc).
    """
    rows = (
        PageUsage.query
        .filter(PageUsage.account_id == account_id)
        .order_by(PageUsage.total_visits.desc())
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        # format avgTimeSpent as "Xm Ys" if you want, else just return float seconds
        avg_time = f"{row.avg_time_spent:.0f}s" if row.avg_time_spent else None

        results.append({
            "page": make_pretty_url(row.pathname),
            "avgTime": avg_time,
            "visits": row.total_visits,
        })

    return results


def get_top_fields(db: Session, account_id: int, days: int = 365, limit: int = 5):
    """
    Aggregate EventsUsage for most-used fields (clicks/inputs).
    Mirrors the UI logic.
    """
    rows = (
        db.session.query(
            EventsUsage.x_path.label("xpath"),        # <-- use x_path
            EventsUsage.pathname.label("pathname"),
            EventsUsage.event_type.label("eventType"), # <-- use event_type
            func.sum(EventsUsage.total_events).label("used"), # <-- use total_events
        )
        .filter(EventsUsage.account_id == account_id)
        .filter(EventsUsage.created_at >= func.now() - text(f"INTERVAL '{days} days'"))
        .group_by(EventsUsage.x_path, EventsUsage.pathname, EventsUsage.event_type)
        .order_by(func.sum(EventsUsage.total_events).desc())
        .limit(limit)
        .all()
    )


    return [
        {
            "action": f"{row.eventType} {row.xpath}",  # or adjust like UI’s parseXPath
            "count": int(row.used or 0),
            "page": make_pretty_url(row.pathname),  # you might want to normalize with makePrettyUrl
        }
        for row in rows
    ]


def get_top_navigation_issues(account_id: int, limit: int = 5):
    """
    Fetch top navigation-related friction issues.
    """
    friction_types = ["BACKTRACKING", "SHORT_DWELL", "LONG_DWELL"]

    rows = (
        JourneyFriction.query
        .filter(JourneyFriction.account_id == account_id)
        .filter(JourneyFriction.friction_type.in_(friction_types))
        .order_by(desc(JourneyFriction.volume))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": row.id,
            "frictionType": row.friction_type.value if hasattr(row.friction_type, "value") else row.friction_type,
            "url": row.url,
            "eventName": row.event_name,
            "volume": row.volume
        }
        for row in rows
    ]

    """
    Fetch top navigation-related friction issues (backtracking, short dwell, long dwell).
    """
    friction_types = ["BACKTRACKING", "SHORT_DWELL", "LONG_DWELL"]

    rows = (
        JourneyFriction.filter(JourneyFriction.account_id == account_id)
        .filter(JourneyFriction.friction_type.in_(friction_types))
        .order_by(desc(JourneyFriction.volume))
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        results.append({
            "id": row.id,
            "frictionType": row.friction_type,
            "url": row.url,                 # optionally normalize with makePrettyUrl
            "eventName": row.event_name,
            "volume": row.volume
        })

    return results


def format_duration(seconds: int) -> str:
    if seconds is None:
        return "N/A"
    m = seconds // 60
    s = seconds % 60
    return f"{m}m {s}s" if m else f"{s}s"


def get_form_usage(account_id: int, days: int = 30, limit: int = 5):
    """
    Port of the GetTopFormDropOffs resolver from Next.js into Flask/SQLAlchemy.
    """

    # base stats
    scoped = (
        FormUsage.query
        .filter(FormUsage.account_id == account_id)
        .filter(FormUsage.created_at >= func.now() - text(f"INTERVAL '{days} days'"))
        .subquery()
    )

    base = (
        db.session.query(
            scoped.c.pathname,
            scoped.c.formHash,
            func.count().label("total"),
            func.count().filter(scoped.c.status == "abandoned").label("abandons"),
            func.count().filter(scoped.c.status == "completed").label("completes"),
            func.percentile_cont(0.5).within_group(scoped.c.duration).filter(scoped.c.status == "completed").label("medianDur")
        )
        .group_by(scoped.c.pathname, scoped.c.formHash)
        .subquery()
    )

    # top drop field
    drops = (
        db.session.query(
            scoped.c.pathname,
            scoped.c.formHash,
            scoped.c.lastField,
            func.count().label("dropCount"),
            func.sum(func.count()).over(partition_by=(scoped.c.pathname, scoped.c.formHash)).label("totalAbandons"),
            func.row_number().over(partition_by=(scoped.c.pathname, scoped.c.formHash),
                                   order_by=func.count().desc()).label("rn")
        )
        .filter(scoped.c.status == "abandoned")
        .filter(scoped.c.lastField.isnot(None))
        .filter(scoped.c.lastField != "")
        .group_by(scoped.c.pathname, scoped.c.formHash, scoped.c.lastField)
        .subquery()
    )

    top_drop = (
        db.session.query(drops)
        .filter(drops.c.rn == 1)
        .subquery()
    )

    # account median duration
    acct = (
        db.session.query(
            func.percentile_cont(0.5).within_group(scoped.c.duration).filter(scoped.c.status == "completed").label("accountMedian")
        )
        .subquery()
    )

    # join them
    rows = (
        db.session.query(
            base.c.pathname,
            base.c.formHash,
            base.c.total,
            base.c.abandons,
            base.c.completes,
            base.c.medianDur,
            top_drop.c.lastField,
            top_drop.c.dropCount,
            top_drop.c.totalAbandons,
            acct.c.accountMedian.label("accountMedian")
        )
        .outerjoin(
            top_drop,
            (top_drop.c.pathname == base.c.pathname) &
            (top_drop.c.formHash == base.c.formHash)
        )
        .order_by(
            (base.c.abandons.cast(db.Float) /
            func.nullif(base.c.total.cast(db.Float), 0)).desc()
        )
        .limit(limit)
        .all()
    )

    # scoring
    MIN_ATTEMPTS = 3
    ABANDON_THRESH = 0.30
    SLOW_ABS = 60
    SLOW_MULT = 1.25
    DROP_SHARE = 0.40
    DROP_MIN = 5

    results = []
    for r in rows:
        total = int(r.total or 0)
        abandons = int(r.abandons or 0)
        completes = int(r.completes or 0)
        completion_rate = math.floor((completes / total) * 100) if total else 0
        median_sec = int(r.medianDur) if r.medianDur is not None else None
        acc_median = int(r.accountMedian) if r.accountMedian is not None else None

        drop_count = int(r.dropCount or 0)
        total_abandons = int(r.totalAbandons or 0)
        drop_pct = (drop_count / total_abandons) if total_abandons else 0

        # scoring logic
        points = 0
        reasons = []
        label, color = "Smooth", "green"

        if total < MIN_ATTEMPTS:
            label, color = "Insufficient data", "gray"
        else:
            abandon_rate = abandons / total if total else 0
            if abandon_rate >= ABANDON_THRESH:
                points += 2
                reasons.append(f"High abandon rate ({abandon_rate:.0%})")

            if median_sec is not None:
                slow_vs_abs = median_sec > SLOW_ABS
                slow_vs_acct = acc_median and median_sec > acc_median * SLOW_MULT
                if slow_vs_abs or slow_vs_acct:
                    points += 1
                    reasons.append(f"Slow median time ({format_duration(median_sec)})")

            if total_abandons >= DROP_MIN and drop_pct >= DROP_SHARE:
                points += 1
                reasons.append(f"Many quits at {r.lastField or 'Unknown'} ({drop_pct:.0%})")

            if points >= 3:
                label, color = "Fix", "red"
            elif points >= 1:
                label, color = "Watch", "amber"

        results.append({
            "page": make_pretty_url(r.pathname),
            "formHash": r.formHash,
            "completionRate": completion_rate,
            "medianTime": format_duration(median_sec) if median_sec else "N/A",
            "dropField": r.lastField or "Unknown",
            "attempts": total,
            "abandonCount": abandons,
            "friction": {"label": label, "color": color, "reasons": reasons}
        })

    return results


def build_summary_for_account(db: Session, account_id: int) -> dict:
    """
    Aggregate data from PageUsage, EventUsage, FormUsage, and JourneyFriction
    into a structured JSON summary.
    """



    top_fields = get_top_fields(db, account_id, days=365, limit=5)
    top_navigation_issues = get_top_navigation_issues(account_id)
    page_usage = get_page_usage(account_id)
    form_usage = get_form_usage(account_id)

    return {
        "pageUsage": page_usage,
        "topNavigationIssues": top_navigation_issues,
        "formUsage": form_usage,
        # "journeyFriction": journey_friction,
        "topFields": top_fields
    }
