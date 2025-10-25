from typing import Dict, List
from datetime import datetime
from models.customer_journey import JourneyStatusEnum
# from models import CustomerJourney  # if you want to annotate element type

def calculate_completion_rate(journey_groups: Dict[int, List]) -> Dict[int, float]:
    """Return {journey_id: completion_rate_percent}."""
    rates: Dict[int, float] = {}
    for journey_id, journeys in journey_groups.items():
        total = len(journeys)
        completed = sum(1 for j in journeys if j.status == JourneyStatusEnum.COMPLETED)
        rate = (completed / total * 100) if total else 0.0
        rates[journey_id] = round(rate, 2)
    return rates


def calculate_completed_journeys(journey_groups: Dict[int, List]) -> Dict[int, int]:
    """Return {journey_id: total_completed_count}."""
    totals: Dict[int, int] = {}
    for journey_id, journeys in journey_groups.items():
        totals[journey_id] = sum(1 for j in journeys if j.status == JourneyStatusEnum.COMPLETED)
    return totals


import numpy as np

def calculate_completion_times(journey_groups: Dict[int, List]) -> Dict[int, float]:
    """
    Returns {journey_id: median_completion_time_ms}.
    Ignores incomplete or invalid durations.
    Median = the 'middle' time most users experience.
    """
    medians = {}
    for journey_id, journeys in journey_groups.items():
        durations = []
        for j in journeys:
            if j.status != JourneyStatusEnum.COMPLETED:
                continue
            start, end = getattr(j, "start_time", None), getattr(j, "end_time", None)
            if not start or not end:
                continue
            delta_ms = max(0.0, (end - start).total_seconds() * 1000.0)
            durations.append(delta_ms)
        medians[journey_id] = round(float(np.median(durations)), 2) if durations else 0.0
    return medians

