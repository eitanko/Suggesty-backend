from typing import List, Tuple, Optional, Dict
from repositories.events import fetch_events_for_customer_journey
from utils.norm_and_compare import compare_elements
from collections import defaultdict

RepeatedTuple = Tuple[str, str, str, int]  # (element, url, session_id, repeat_count)

def detect_repeated_behavior(
    session,
    cj_id: str,
    last_ideal_step: Optional[int] = None,
    threshold: int = 3,
    *,
    backtrack_window: int = 2,
) -> List[RepeatedTuple]:
    """
    Scan a customer journey's ordered events and detect repeated interactions
    on the same (url + element). A sequence counts as "repeated" if there are
    at least `threshold` *additional* consecutive identical events after the first.
    Returns a list of (element, url, session_id, repeat_count).
    """
    journey_events = fetch_events_for_customer_journey(session, cj_id)
    if not journey_events:
        return []

    # Start scanning a bit before the last ideal step to catch loops around it.
    if last_ideal_step is not None:
        start_index = max(0, last_ideal_step - backtrack_window)
    else:
        start_index = 0

    events_to_scan = journey_events[start_index:]
    if not events_to_scan:
        return []

    repeated_steps: List[RepeatedTuple] = []
    current_event = events_to_scan[0]
    counter = 0  # number of repeats *after* the first normal interaction

    for event in events_to_scan[1:]:
        if (
            event.url == current_event.url
            and compare_elements(event.x_path, current_event.x_path)
        ):
            counter += 1
        else:
            if counter >= threshold:
                repeated_steps.append((
                    current_event.x_path,
                    current_event.url,
                    current_event.session_id,
                    counter,
                ))
            current_event = event
            counter = 0

    # tail sequence
    if counter >= threshold:
        repeated_steps.append((
            current_event.elements_chain.split(';')[0],
            current_event.url,
            current_event.session_id,
            counter,
        ))

    return repeated_steps




def calculate_repeated_behavior_all_journeys(
    journeys,
    session,
    *,
    threshold: int = 3,
    last_ideal_step: int = 1,
):
    """
    For all given CustomerJourney rows, detect repeated behavior.
    Returns: { parent_journey_id: [ (element, url, session_id, repeat_count), ... ] }
    """
    repeated_events_by_journey: Dict[int, List[RepeatedTuple]] = defaultdict(list)

    for cj in journeys:
        reps = detect_repeated_behavior(
            session,
            cj.id,
            last_ideal_step=last_ideal_step,
            threshold=threshold,
        )
        if reps:
            # Use the FK to the parent Journey as the dict key
            repeated_events_by_journey[cj.journey_id].extend(reps)

    return repeated_events_by_journey
