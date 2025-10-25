from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from calculators.repeats import detect_repeated_behavior
from models.customer_journey import JourneyStatusEnum

DropOffDistribution = Dict[int, int]
DropOffReasons = Dict[int, List[Tuple[str, str, str, int]]]  # (element, url, session_id, repeat_count)
DropOffEvents = List[Tuple[str, str, str]]  # (element, url, session_id)

def calculate_drop_off_distribution(
    journey_group: Iterable[Any],
    session,
    ideal_path_steps: List[Dict[str, Any]],
    *,
    repeats_threshold: int = 3,
    assume_current_step_is_next_to_attempt: bool = True,
) -> Tuple[DropOffDistribution, DropOffReasons, DropOffEvents]:
    """
    Compute drop-off data for a set of CustomerJourneys.

    Semantics:
      - We assume `current_step_index` is the *next* step the user attempted (1-based).
        Therefore the *last ideal step reached* is `current_step_index - 1` (0-based).
      - If `assume_current_step_is_next_to_attempt=False`, we treat `current_step_index`
        as already completed and use it directly (0-based).

    Returns:
      distribution: {zero_based_step_index -> count}
      drop_off_reasons: {zero_based_step_index -> list of (element, url, session_id, repeat_count)}
      drop_off_events: [(element, url, session_id)] for the last ideal step before the drop
    """
    distribution: DropOffDistribution = defaultdict(int)
    drop_off_reasons: DropOffReasons = defaultdict(list)
    drop_off_events: DropOffEvents = []

    total_steps = len(ideal_path_steps)

    for journey in journey_group:
        if journey.status != JourneyStatusEnum.FAILED or journey.current_step_index is None:
            continue

        # Map to zero-based index against ideal steps
        if assume_current_step_is_next_to_attempt:
            step_idx = (journey.current_step_index - 1)  # user failed between prev->current
        else:
            step_idx = journey.current_step_index  # treat as last completed

        # Clamp to valid range so we don’t crash on bad data
        # If step_idx < 0, pin to 0; if step_idx >= total_steps, pin to last step.
        if total_steps == 0:
            continue  # no ideal steps; nothing to attribute
        clamped_idx = max(0, min(step_idx, total_steps - 1))

        distribution[clamped_idx] += 1

        # Repeated event reasons (scan near the last ideal step index)
        reasons = detect_repeated_behavior(session, journey.id, last_ideal_step=clamped_idx, threshold=repeats_threshold)
        # Dedup but keep stable order by first-seen (avoid nondeterministic set order)
        seen = set()
        deduped: List[Tuple[str, str, str, int]] = []
        for r in reasons:
            # r is expected as (element, url, session_id, repeat_count)
            if r not in seen:
                seen.add(r)
                deduped.append(r)
        drop_off_reasons[clamped_idx].extend(deduped)

        # Attribute the drop to the last ideal step before failure
        last_ideal = ideal_path_steps[clamped_idx]
        drop_off_events.append((last_ideal["element"], last_ideal["url"], journey.session_id))

    return dict(distribution), drop_off_reasons, drop_off_events
