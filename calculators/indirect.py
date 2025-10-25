from collections import defaultdict
from typing import Dict, List, Tuple
from models.customer_journey import CompletionType, JourneyStatusEnum

def calculate_indirect_completion_rate(journey_groups) -> Dict[int, float]:
    """
    Calculates the indirect completion rate per journey_id as PERCENT (0–100).
    Returns: {journey_id: indirect_rate_percent}
    """
    rates: Dict[int, float] = {}
    for journey_id, journeys in journey_groups.items():
        completed = sum(1 for j in journeys if j.status == JourneyStatusEnum.COMPLETED)
        indirect  = sum(1 for j in journeys
                        if j.status == JourneyStatusEnum.COMPLETED
                        and j.completion_type == CompletionType.INDIRECT)
        rates[journey_id] = round((indirect / completed * 100) if completed else 0.0, 2)
    return rates


from collections import defaultdict
from typing import List, Dict, Tuple

def extract_frequent_alternatives(indirect_completed: List, session) -> Dict[str, List[Tuple[str, float]]]:
    """
    For each indirectly completed journey (CustomerJourney objects), find events
    that are NOT part of the ideal path (is_match == False or xPath not in ideal steps).
    Returns per-URL lists of (xPath, frequency) where frequency = (#journeys containing this event) / total_indirect.
    Example: { "/page-b": [("//div[@class='promo']", 0.5), ...] }
    """
    alt_event_counts: Dict[Tuple[str, str], int] = defaultdict(int)
    total_indirect = len(indirect_completed)
    if total_indirect == 0:
        return {}

    for journey in indirect_completed:
        seen_this_session = set()
        event_sequence = get_event_sequence_for_customer(session, journey)  # list of dicts per event

        # Build set of ideal xPaths for this journey
        ideal_xpaths = {step.x_path for step in journey.journey.steps if getattr(step, "x_path", None)}

        for ev in event_sequence:
            ev_xpath = ev.get("xPath")
            ev_url = ev.get("url")
            ev_is_match = ev.get("is_match", False)

            # Skip events that are part of the ideal path
            if ev_is_match or (ev_xpath in ideal_xpaths):
                continue

            # Count each (xPath,url) once per journey
            key = (ev_xpath, ev_url)
            if key not in seen_this_session and ev_xpath:
                alt_event_counts[key] += 1
                seen_this_session.add(key)

    # Group and normalize by frequency
    result: Dict[str, List[Tuple[str, float]]] = {}
    for (xPath, url), count in alt_event_counts.items():
        freq = round(count / total_indirect, 2)
        result.setdefault(url, []).append((xPath, freq))

    # Sort each URL’s list by frequency descending
    for url in result:
        result[url].sort(key=lambda t: t[1], reverse=True)

    return result



def get_event_sequence_for_customer(session, journey):
    """
    Given a CustomerJourney object, returns its events ordered by timestamp.
    Each event is a dict with url, element, xPath, timestamp (ms), is_match, session_id, event_id.
    """
    from models import Event  # local import to avoid circulars
    events = (session.query(Event)
              .filter(Event.customer_journey_id == journey.id)
              .order_by(Event.timestamp)
              .all())

    return [{
        "url": e.url,
        "element": e.elements_chain,
        "xPath": e.x_path,
        "timestamp": int(e.timestamp.timestamp() * 1000),
        "is_match": bool(e.is_match),
        "session_id": e.session_id,
        "event_id": e.id
    } for e in events]
