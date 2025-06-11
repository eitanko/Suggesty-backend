from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from models import CustomerJourney, JourneyAnalytics, JourneyStatusEnum, Event
from models.customer_journey import FrictionType, JourneyFriction, CompletionType
from utils import compare_elements  # a custom function to check if two element chains are equivalent
from collections import defaultdict

def calculate_completion_times(journey_groups):
    """
    Calculate completion times for each journeyId.
    Completion time is measured as (end_time - start_time) for each completed journey.
    """
    completion_times = {}
    print('Calculate completion times...')

    # Ensure journey_groups is a dictionary
    if not isinstance(journey_groups, dict):
        raise ValueError("journey_groups should be a dictionary.")

    for journey_id, journeys in journey_groups.items():
        total_time_ms = 0
        completed_journeys = 0

        for journey in journeys:
            # Calculate time only for completed journeys
            if journey.status == JourneyStatusEnum.COMPLETED:
                # Calculate time difference in milliseconds
                completion_time = (journey.end_time - journey.start_time).total_seconds() * 1000
                total_time_ms += completion_time
                completed_journeys += 1

        # Calculate the average completion time (if there are any completed journeys)
        if completed_journeys > 0:
            average_completion_time_ms = total_time_ms / completed_journeys
        else:
            average_completion_time_ms = 0

        # Store the result
        completion_times[journey_id] = round(average_completion_time_ms, 2)

    return completion_times

def insert_journey_analytics(
    session: Session,
    journey_id: str,
    completion_rate: float,
    total_completions: int,
    total_users: int,
    indirect_rate: float,
    completion_time_ms: int,
    total_steps: int,
    drop_off_distribution: dict,
    friction_score: float,
    frequent_alt_paths: dict,
    step_insights: dict
):
    """
    Insert or update the JourneyAnalytics data for a specific journey_id.
    """
    # Try to find an existing record for the given journey_id
    journey_analytics = session.query(JourneyAnalytics).filter(JourneyAnalytics.journey_id  == journey_id).first()

    if journey_analytics:
        # the record exists, update it
        print(f"Updating JourneyAnalytics for journey {journey_id}")
        journey_analytics.completion_rate=completion_rate,
        journey_analytics.total_completions=total_completions,
        journey_analytics.indirect_rate=indirect_rate,
        journey_analytics.completion_time_ms=completion_time_ms,
        journey_analytics.total_steps=total_steps,
        journey_analytics.total_users = total_users,
        journey_analytics.drop_off_distribution=drop_off_distribution,
        journey_analytics.friction_score=friction_score,
        journey_analytics.frequent_alt_paths=frequent_alt_paths,
        journey_analytics.step_insights=step_insights
        journey_analytics.created_at=datetime.utcnow(),
        journey_analytics.updated_at=datetime.utcnow()
    else:
        # If the record doesn't exist, insert a new one
        print(f"Creating new JourneyAnalytics for journey {journey_id}")
        journey_analytics = JourneyAnalytics(
            journey_id=journey_id,
            completion_rate=completion_rate,
            total_completions=total_completions,
            total_users=total_users,
            indirect_rate=indirect_rate,
            completion_time_ms=completion_time_ms,
            total_steps=total_steps,
            drop_off_distribution=drop_off_distribution,
            friction_score=friction_score,
            frequent_alt_paths=frequent_alt_paths,
            step_insights=step_insights,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(journey_analytics)
    session.commit()
    return journey_analytics

def calculate_completion_rate(journey_groups):
    """
    Calculate completion rate for each journeyId.
    """
    completion_rates = {}
    print('Running report....')

    for journey_id, journeys in journey_groups.items():
        # Ensure we have a list of journeys
        if not isinstance(journeys, list):
            print(f"Skipping journey_id {journey_id}: not a list of journeys.")
            continue

        total_journeys = len(journeys)
        completed_journeys = len([journey for journey in journeys if journey.status == JourneyStatusEnum.COMPLETED])

        # Avoid division by zero
        if total_journeys == 0:
            completion_rate = 0
        else:
            completion_rate = (completed_journeys / total_journeys) * 100

        completion_rates[journey_id] = round(completion_rate, 2)

    return completion_rates


######### CALCULATE REPEATED EVENTS #########

def detect_repeated_behavior(session: Session, cj_id: str, last_ideal_step: Optional[int] = None, threshold: int = 3) -> List[Tuple[str, str, int]]:
    journey_events = session.query(Event)\
        .filter_by(customer_journey_id=cj_id)\
        .order_by(Event.timestamp).all()

    if not journey_events:
        return []

    start_index = max(0, last_ideal_step - 2) if last_ideal_step else 0
    events_to_scan = journey_events[start_index:]

    if not events_to_scan:
        return []

    repeated_steps = []
    current_event = events_to_scan[0]
    counter = 0

    for event in events_to_scan[1:]:
        if event.url == current_event.url and compare_elements(event.elements_chain, current_event.elements_chain):
            counter += 1  # This is a repetition
        else:
            if counter >= threshold:
                # Add only if repeated (excluding the first normal interaction)
                repeated_steps.append((
                    current_event.elements_chain.split(';')[0],
                    current_event.url,
                    current_event.session_id,
                    counter
                ))
            # Reset for next sequence
            current_event = event
            counter = 0

    # Final check after loop ends
    if counter >= threshold:
        repeated_steps.append((
            current_event.elements_chain.split(';')[0],
            current_event.url,
            current_event.session_id,
            counter
        ))

    return repeated_steps

def calculate_repeated_behavior_all_journeys(journeys: List[CustomerJourney], session: Session) -> Dict[str, List[Tuple[str, str, int]]]:
    """
    Detect repeated behavior for all journeys (completed and failed).
    Returns: { journey_id: [ (element_chain, url, count), ... ] }
    """
    repeated_events_by_journey = defaultdict(list)

    for journey in journeys:
        repeated_events = detect_repeated_behavior(session, journey.id, last_ideal_step=1)
        if repeated_events:
            repeated_events_by_journey[journey.journey_id].extend(repeated_events)

    return repeated_events_by_journey

######### CALCULATE TIME ON EACH STEP #########

def get_admin_path_for_journey(session, journey_id: int):
    """
    Retrieves the ideal path for a given journey_id using the Step table.
    Returns a list of steps including url, element, and an artificial timestamp for ordering.
    """
    from models import Step  # Adjust import path as needed

    steps = (
        session.query(Step)
        .filter(Step.journey_id == journey_id)
        .order_by(Step.index)
        .all()
    )

    return [
        {
            "step": step.index,
            "name": step.name,
            "url": step.url,
            "element": step.elements_chain,
            "timestamp": step.created_at
        }
        for i, step in enumerate(steps)
    ]

def get_event_sequence_for_customer(session, journey):
    """
    Given a CustomerJourney object, returns a list of its events ordered by timestamp.
    Each event is represented as a dict with url, element, and timestamp (in ms).
    """
    from models import Event  # Ensure your Event model is correctly imported

    events = (
        session.query(Event)
        .filter(Event.customer_journey_id == journey.id)
        .order_by(Event.timestamp)
        .all()
    )

    return [
        {
            "url": event.url,
            "element": event.elements_chain,
            "timestamp": int(event.timestamp.timestamp() * 1000), # Convert to milliseconds
            "is_match": event.is_match,
            "session_id": event.session_id,
            "event_id": event.id  # Include ID for reference if needed

        }
        for event in events
    ]

def generate_step_insights_from_ideal_path(
    ideal_path_steps,
    completed_journeys,
    threshold=3,
    repeated_events=None,
    drop_off_events=None
)-> Tuple[Dict, List[Tuple[str, str, str, float]]]:
    """
    Builds a step_insights JSON for a journey based on:
    - the ideal admin path
    - completed user journeys
    Detects delays as anomalies if actual time > threshold * ideal time.
    """
    from statistics import mean
    from utils.norm_and_compare import compare_elements

    # Step 1: Simulate ideal durations based on admin path (600ms per step assumed)
    ideal_durations = {}
    for i in range(1, len(ideal_path_steps)):
        ideal_prev = ideal_path_steps[i - 1]
        ideal_curr = ideal_path_steps[i]
        key = (ideal_prev["url"], ideal_prev["element"])
        ideal_durations[key] = ((ideal_curr["timestamp"] - ideal_prev["timestamp"]).total_seconds() * 1000)

    # Step 2: Measure actual times in completed journeys
    from collections import defaultdict

    step_stats = defaultdict(lambda: {
        "times": [],
        "delayed_sessions": set(),
        "all_sessions": set()
    })
    delayed_events = []  # ✅ Collect per-session delays here

    for journey in completed_journeys:
        session_id = journey[0].get("session_id")  # assumes session_id is consistent within the journey
        for i in range(1, len(journey)):
            prev = journey[i - 1]
            curr = journey[i]
            duration = curr["timestamp"] - prev["timestamp"]

            for ideal_step_index in range(len(ideal_path_steps) - 1):
                ideal_step = ideal_path_steps[ideal_step_index]
                ideal_key = (ideal_step["url"], ideal_step["element"])

                if prev["url"] == ideal_step["url"] and compare_elements(ideal_step["element"], prev["element"]) and prev.get("is_match", False):
                    step_stats[ideal_key]["times"].append(duration)
                    step_stats[ideal_key]["all_sessions"].add(session_id)

                    if duration > threshold * ideal_durations.get(ideal_key, float("inf")):
                        step_stats[ideal_key]["delayed_sessions"].add(session_id)
                        delayed_events.append((
                            prev["element"],
                            prev["url"],
                            session_id,
                            duration
                        ))
                    break  # stop after first match

    # Step 3: Assemble final structure
    step_insights = {}
    for i in range(len(ideal_path_steps)):
        curr = ideal_path_steps[i]
        key = (curr["url"], curr["element"])

        # stats = step_stats.get(key, {"times": [], "delayed": 0, "count": 0})
        stats = step_stats.get(key, {
            "times": [],
            "delayed_sessions": set(),
            "all_sessions": set()
        })
        avg_time = mean(stats["times"]) if stats["times"] else 0
        delay_rate = (
            len(stats["delayed_sessions"]) / len(stats["all_sessions"])
            if stats["all_sessions"]
            else 0
        )
        anomalies = []
        if delay_rate:
            anomalies.append({
                "type": "delay",
                "severity": "high" if delay_rate > 0.5 else "medium",
                "detail": f"{int(delay_rate * 100)}% of users are delayed"
            })
            print(f"Anomaly detected for step {i+1}: {anomalies[-1]['detail']}")

        # friction_key = (curr["element"], curr["url"]) # Adjusted to match the repeated_events structure

        repeated_rate = 0
        for (element, url), rate in repeated_events.items():
            if url == curr["url"] and compare_elements(curr["element"],element):
                repeated_rate = rate
                break

        drop_off_rate = 0
        for (element, url), rate in drop_off_events.items():
            if url == curr["url"] and compare_elements(curr["element"],element):
                drop_off_rate = rate
                break

        # Initialize `element` to avoid referencing before assignment
        element = curr["element"]

        # Add anomalies
        if repeated_rate:
            anomalies.append({
                "type": "repetition",
                "severity": "high" if repeated_rate > 0.5 else "medium",
                "detail": f"{int(repeated_rate * 100)}% of users repeated this step"
            })

        if drop_off_rate:
            anomalies.append({
                "type": "drop_off",
                "severity": "high" if drop_off_rate > 0.5 else "medium",
                "detail": f"{int(drop_off_rate * 100)}% of users dropped off here"
            })

        next_step = f"step_{i + 2}" if i < len(ideal_path_steps) - 1 else None

        step_insights[f"step_{i+1}"] = {
            "name": curr["name"],
            "url": curr["url"],
            "element": element,
            "avg_time_ms": round(avg_time),
            "drop_off_rate": round(drop_off_rate, 2),
            "repeated_rate": round(repeated_rate, 2),
            "anomalies": anomalies,
            "paths": {
                "next_step": next_step,
                "indirect_transitions": {},
                "drop_off": False
            }
        }
    # 🐢 Collect per-session delayed events
    delayed_events = []  # List of (element, url, session_id, delay_ms)

    return step_insights, delayed_events


def calculate_drop_off_distribution(journey_group, session: Session):
    """
    Calculate drop-off distribution for a list of CustomerJourneys.
    Returns:
      - step distribution (step → count),
      - drop-off reasons (step → repeated event list),
      - drop-off event elements (list of tuples: (elements_chain, url)).
    """
    distribution = defaultdict(int)
    drop_off_reasons = defaultdict(list)
    drop_off_events = []  # ← New: store (elements_chain, url) of last event before drop-off

    for journey in journey_group:
        if journey.status == JourneyStatusEnum.FAILED and journey.current_step_index is not None:
            step_number = journey.current_step_index + 1
            distribution[step_number] += 1

            # Repeated event reasons
            reasons = detect_repeated_behavior(session, journey.id, step_number)
            drop_off_reasons[step_number].extend(reasons)

            # Get last event before drop
            last_event = session.query(Event).filter_by(customer_journey_id=journey.id).order_by(Event.timestamp.desc()).first()
            if last_event:
                drop_off_events.append((last_event.elements_chain.split(';')[0], last_event.url, last_event.session_id))

    # Remove duplicates from reasons
    for step, reasons in drop_off_reasons.items():
        drop_off_reasons[step] = list(set(reasons))

    return dict(distribution), drop_off_reasons, drop_off_events

def calculate_completed_journeys(journey_groups: dict):
    """
    Calculate the total number of completed journeys for each journey_id from the grouped journeys.
    """
    total_completed_by_journey = {}

    for journey_id, journeys in journey_groups.items():
        # Count the number of completed journeys for this journey_id
        total_completed = len([journey for journey in journeys if journey.status == JourneyStatusEnum.COMPLETED])

        total_completed_by_journey[journey_id] = total_completed

    return total_completed_by_journey

def fetch_customer_journeys_by_journey_id(session: Session):
    """
    Fetch customer journeys grouped by journeyId and filter by 'COMPLETED' and 'IN_PROGRESS'.
    """
    journeys = session.query(CustomerJourney).filter(
        CustomerJourney.status.in_([JourneyStatusEnum.COMPLETED, JourneyStatusEnum.FAILED])
    ).all()

    # Group journeys by journeyId
    grouped_by_journey_id = defaultdict(list)
    for journey in journeys:
        grouped_by_journey_id[journey.journey_id].append(journey)

    return grouped_by_journey_id

def upsert_journey_friction(session, journey_id, event_name, url, event_details, session_id, friction_type, friction_rate, total_users, volume):
    """
    Upserts a JourneyFriction record by either updating an existing entry or inserting a new one.
    Matching is done on journey_id, event_name, url, event_details, and friction_type.
    """
    existing = session.query(JourneyFriction).filter(
        JourneyFriction.journey_id == journey_id,
        JourneyFriction.event_name == event_name,
        JourneyFriction.url == url,
        JourneyFriction.event_details == event_details,
        JourneyFriction.friction_type == friction_type.value  # .value if it's an Enum
    ).first()

    if existing:
        # Update existing row
        existing.friction_rate = friction_rate
        existing.total_users = total_users
        existing.volume = volume
        existing.updated_at = datetime.utcnow()
        print(f"Updated JourneyFriction for {event_name} on {url}")
    else:
        # Insert new row
        new_entry = JourneyFriction(
            journey_id=journey_id,
            event_name=event_name,
            url=url,
            event_details=event_details,
            session_id=session_id,
            friction_type=friction_type,
            volume=volume
        )
        new_entry.friction_rate = friction_rate
        new_entry.total_users = total_users
        session.add(new_entry)
        print(f"Inserted new JourneyFriction for {event_name} on {url}")

def calculate_indirect_completion_rate(journey_groups):
    """
    Calculates the indirect completion rate per journey_id.

    Returns: dict of journey_id -> indirect_rate (0–1 float)
    """
    rates = {}

    for journey_id, journeys in journey_groups.items():
        completed = [j for j in journeys if j.status == JourneyStatusEnum.COMPLETED]
        indirect = [j for j in completed if j.completion_type == CompletionType.INDIRECT]

        if completed:
            rates[journey_id] = len(indirect) / len(completed) * 100
        else:
            rates[journey_id] = 0

    return rates




def extract_frequent_alternatives(indirect_completed, session) -> Dict[str, List[Tuple[str, float]]]:
    """
    For each event in indirectly completed journeys, count events not in the ideal path
    (i.e., is_match == False) and calculate their frequency per URL.
    """
    alt_event_counts = defaultdict(int)
    total_indirect = len(indirect_completed)

    for customer_journey_id in indirect_completed:
        seen = set()
        event_sequence = get_event_sequence_for_customer(session, customer_journey_id)

        for event in event_sequence:
            if not event["is_match"]:
                key = (event["element"], event["url"])
                if key not in seen:
                    alt_event_counts[key] += 1
                    seen.add(key)

    # Format result: group by URL, show top alternative elements and their frequency
    result = {}
    for (element, url), count in alt_event_counts.items():
        result.setdefault(url, []).append((element, round(count / total_indirect, 2)))

    return result


def process_journey_metrics(session: Session):
    """
    Process metrics for each journey_id: store aggregate friction in JourneyFriction,
    and update JourneyAnalytics with a step_insights JSON based on the ideal path.
    """
    journey_groups = fetch_customer_journeys_by_journey_id(session)
    completion_rates = calculate_completion_rate(journey_groups)
    total_completed = calculate_completed_journeys(journey_groups)
    completion_times = calculate_completion_times(journey_groups)
    indirect_rates = calculate_indirect_completion_rate(journey_groups)

    for journey_id, customer_journeys in journey_groups.items():
        completed_journeys = [j for j in customer_journeys if j.status == JourneyStatusEnum.COMPLETED]
        total_users = len(customer_journeys)
        total_completions = total_completed.get(journey_id, 0)
        completion_rate = completion_rates.get(journey_id, 0)
        completion_time = completion_times.get(journey_id, 0)
        indirect_rate = indirect_rates.get(journey_id, 0)

        # 🔁 REPEATED events (for JourneyFriction)
        repeated_events_by_journey = calculate_repeated_behavior_all_journeys(customer_journeys, session)
        aggregated_repeats = defaultdict(lambda: {"volume": 0, "total_users": total_users})
        for step, events in repeated_events_by_journey.items():
            for element_details, url, session_id, _ in events:
                aggregated_repeats[(element_details, url, session_id)]["volume"] += 1

        for (element_details, url, session_id), data in aggregated_repeats.items():
            upsert_journey_friction(
                session, str(journey_id), "repeated", url, element_details, session_id,
                FrictionType.REPEATED, (data["volume"] / total_users) * 100,
                total_users, data["volume"]
            )

        # 📉 DROP-OFF events (for JourneyFriction)
        _, _, drop_off_events = calculate_drop_off_distribution(customer_journeys, session)
        drop_off_counts = defaultdict(int)
        for element_details, url, session_id in drop_off_events:
            drop_off_counts[(element_details, url, session_id)] += 1

        for (element_details, url, session_id), volume in drop_off_counts.items():
            upsert_journey_friction(
                session, str(journey_id), "drop_off", url, element_details, session_id,
                FrictionType.DROP_OFF, (volume / total_users) * 100,
                total_users, volume
            )

        repeated_lookup = {
            (element_details, url): (data["volume"] / total_users)
            for (element_details, url, session_id), data in aggregated_repeats.items()
        }

        drop_off_lookup = {
            (element_details, url): (volume / total_users)
            for (element_details, url, session_id), volume in drop_off_counts.items()
        }

        # 🧠 Generate full step insights funnel JSON
        ideal_path = get_admin_path_for_journey(session, journey_id)
        direct_completed = [j for j in completed_journeys if j.completion_type == CompletionType.DIRECT]
        completed_sequences = [get_event_sequence_for_customer(session, j) for j in direct_completed]
        step_insights, delayed_events = generate_step_insights_from_ideal_path(
            ideal_path_steps=ideal_path,
            completed_journeys=completed_sequences,
            threshold=4,
            repeated_events=repeated_lookup,
            drop_off_events=drop_off_lookup
        )


        indirect_completed = [j for j in completed_journeys if j.completion_type == CompletionType.INDIRECT]
        frequent_alt_paths = extract_frequent_alternatives(indirect_completed, session)

        # 📊 Store journey analytics including step_insights
        insert_journey_analytics(
            session=session,
            journey_id=str(journey_id),
            completion_rate=completion_rate,
            total_completions=total_completions,
            total_users=total_users,
            indirect_rate=indirect_rate,
            completion_time_ms=completion_time,
            total_steps=0,
            drop_off_distribution={},  # already saved above if needed separately
            friction_score=0,
            frequent_alt_paths=frequent_alt_paths,
            step_insights=step_insights
        )

    return completion_rates





