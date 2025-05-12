from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from models import CustomerJourney, JourneyAnalytics, JourneyStatusEnum, Event
from models.customer_journey import FrictionType, JourneyFriction, CompletionType
from utils import compare_elements  # a custom function to check if two element chains are equivalent
from collections import defaultdict
from itertools import groupby
from operator import attrgetter

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
    indirect_rate: float,
    completion_time_ms: int,
    steps_completed: int,
    total_steps: int,
    drop_off_distribution: dict,
    slowest_step: int,
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
        journey_analytics.steps_completed=steps_completed,
        journey_analytics.total_steps=total_steps,
        journey_analytics.drop_off_distribution=drop_off_distribution,
        journey_analytics.slowest_step=slowest_step,
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
            indirect_rate=indirect_rate,
            completion_time_ms=completion_time_ms,
            steps_completed=steps_completed,
            total_steps=total_steps,
            drop_off_distribution=drop_off_distribution,
            slowest_step=slowest_step,
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

    # Assign pseudo-timestamps based on index (e.g., 0ms, 600ms, 1200ms)
    return [
        {
            "step": step.index,
            "url": step.url,
            "element": step.elements_chain,
            "timestamp": i * 600  # 600ms per step is an arbitrary placeholder
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
            "timestamp": int(event.timestamp.timestamp() * 1000)  # Convert to milliseconds
        }
        for event in events
    ]

# 👇to be deleted ...
def calculate_indirect_completion_rate(analytics):
    completed = [a for a in analytics if a.match_type in ("DIRECT", "INDIRECT")]
    indirect = [a for a in analytics if a.match_type == "INDIRECT"]
    return len(indirect) / len(completed) if completed else 0

# 👇to be deleted ...
def compute_ideal_step_timings(session, journey_id):
    """
    Calculate ideal step timings based on successful journeys.
    Returns: {step_number: avg_time_in_ms}
    """
    ideal_timings = defaultdict(list)

    # Fetch completed journeys for the given journey_id
    completed_journeys = session.query(CustomerJourney).filter(
        CustomerJourney.journey_id == journey_id,
        CustomerJourney.status == JourneyStatusEnum.COMPLETED
    ).all()

    # Loop through completed journeys to calculate step times
    for journey in completed_journeys:
        journey_steps = session.query(Event).filter_by(customer_journey_id=journey.id).order_by(Event.timestamp).all()

        for i in range(1, len(journey_steps)):
            # Calculate the time spent between each consecutive step
            step_start_time = journey_steps[i - 1].timestamp
            step_end_time = journey_steps[i].timestamp
            time_spent = (step_end_time - step_start_time).total_seconds() * 1000  # in ms

            # Store the time spent for this step number
            ideal_timings[i].append(time_spent)

    # Calculate the average time for each step
    for step_number, times in ideal_timings.items():
        ideal_timings[step_number] = sum(times) / len(times) if times else 0

    return ideal_timings

# 👇to be deleted ...
def detect_delayed_steps(session, journey_id, ideal_timings, threshold=1.5):
    """
    Detect delayed steps for all customer journeys of a given journey_id.
    Returns: { customer_journey_id: [ (step_number, actual_time, ideal_time) ] }
    """
    delayed_by_cj = {}

    # Fetch all events for the journey_id, joined with CustomerJourney
    events = (
        session.query(Event)
        .join(CustomerJourney, CustomerJourney.id == Event.customer_journey_id)
        .filter(CustomerJourney.journey_id == journey_id)
        .order_by(Event.customer_journey_id, Event.timestamp)
        .all()
    )

    # Group events by customer_journey_id
    for cj_id, group in groupby(events, key=attrgetter('customer_journey_id')):
        step_events = list(group)
        delayed_steps = []

        for i in range(1, len(step_events)):
            step_start_time = step_events[i - 1].timestamp
            step_end_time = step_events[i].timestamp
            actual_time = (step_end_time - step_start_time).total_seconds() * 1000

            ideal_time = ideal_timings.get(i, 0)

            if ideal_time > 0 and actual_time > threshold * ideal_time:
                delayed_steps.append((i, actual_time, ideal_time))

        if delayed_steps:
            delayed_by_cj[cj_id] = delayed_steps

    return delayed_by_cj


    return delayed_steps

# 👇to be deleted ...
def upsert_delayed_steps(session, journey_id, delayed_steps, total_users):
    """
    Upsert delayed steps into JourneyFriction table.
    """
    for step_number, actual_time, ideal_time in delayed_steps:
        # Calculate friction rate as the percentage of users who experienced the delay
        volume = 1  # Since we are considering one journey per time
        friction_rate = (volume / total_users) * 100

        # Call upsert to insert/update delayed friction data into JourneyFriction
        upsert_journey_friction(
            session=session,
            journey_id=str(journey_id),
            event_name=f"step_{step_number}",
            url="N/A",  # or the page URL where this step happens
            event_details=f"Step {step_number} - Delayed",
            friction_type=FrictionType.DELAYED,
            friction_rate=friction_rate,
            total_users=total_users,
            volume=volume
        )


def generate_step_insights_from_ideal_path(ideal_path_steps, completed_journeys, threshold=3):
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
        prev = ideal_path_steps[i - 1]
        curr = ideal_path_steps[i]
        key = (prev["url"], prev["element"])
        ideal_durations[key] = curr["timestamp"] - prev["timestamp"]

    # Step 2: Measure actual times in completed journeys
    step_stats = defaultdict(lambda: {"times": [], "delayed": 0, "count": 0})
    for journey in completed_journeys:
        for i in range(1, len(journey)):
            prev = journey[i - 1]
            curr = journey[i]
            duration = curr["timestamp"] - prev["timestamp"]

            for ideal_step_index in range(len(ideal_path_steps) - 1):
                ideal_step = ideal_path_steps[ideal_step_index]
                ideal_key = (ideal_step["url"], ideal_step["element"])

                if prev["url"] == ideal_step["url"] and compare_elements(ideal_step["element"], prev["element"]):
                    step_stats[ideal_key]["times"].append(duration)
                    step_stats[ideal_key]["count"] += 1
                    if duration > threshold * ideal_durations.get(ideal_key, float("inf")):
                        step_stats[ideal_key]["delayed"] += 1
                    break  # stop after first match

    # Step 3: Assemble final structure
    step_insights = {}
    for i in range(len(ideal_path_steps) - 1):
        curr = ideal_path_steps[i]
        next_step = ideal_path_steps[i + 1]
        key = (curr["url"], curr["element"])
        stats = step_stats.get(key, {"times": [], "delayed": 0, "count": 0})

        avg_time = mean(stats["times"]) if stats["times"] else 0
        delay_rate = stats["delayed"] / stats["count"] if stats["count"] else 0

        anomalies = []
        if delay_rate > 0.2:
            anomalies.append({
                "type": "delay",
                "severity": "high" if delay_rate > 0.5 else "medium",
                "detail": f"{int(delay_rate * 100)}% of users are delayed"
            })
            print(f"Anomaly detected for step {i+1}: {anomalies[-1]['detail']}")

        step_insights[f"step_{i+1}"] = {
            "url": curr["url"],
            "element": curr["element"],
            "avg_time_ms": round(avg_time),
            "drop_off_rate": 0.0,  # Optional: to be filled
            "repeated_rate": 0.0,  # Optional: to be filled
            "anomalies": anomalies,
            "paths": {
                "next_step": f"step_{i+2}",
                "indirect_transitions": {},
                "drop_off": False
            }
        }

    return step_insights


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
            last_event = session.query(Event).filter_by(customer_journey_id=journey.id)\
                .order_by(Event.timestamp.desc()).first()
            if last_event:
                drop_off_events.append((last_event.elements_chain.split(';')[0], last_event.url))

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

def upsert_journey_friction(session, journey_id, event_name, url, event_details, friction_type, friction_rate, total_users, volume):
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
            friction_type=friction_type,
            volume=volume
        )
        new_entry.friction_rate = friction_rate
        new_entry.total_users = total_users
        session.add(new_entry)
        print(f"Inserted new JourneyFriction for {event_name} on {url}")

def process_journey_metrics(session: Session):
    """
    Process metrics for each journey_id: store aggregate friction in JourneyFriction,
    and update JourneyAnalytics with a step_insights JSON based on the ideal path.
    """
    journey_groups = fetch_customer_journeys_by_journey_id(session)
    completion_rates = calculate_completion_rate(journey_groups)
    total_completed = calculate_completed_journeys(journey_groups)
    completion_times = calculate_completion_times(journey_groups)

    for journey_id, customer_journeys in journey_groups.items():
        completed_journeys = [j for j in customer_journeys if j.status == JourneyStatusEnum.COMPLETED]
        total_users = len(customer_journeys)
        total_completions = total_completed.get(journey_id, 0)
        completion_rate = completion_rates.get(journey_id, 0)
        completion_time = completion_times.get(journey_id, 0)

        # 🔁 REPEATED events (for JourneyFriction)
        repeated_events_by_journey = calculate_repeated_behavior_all_journeys(customer_journeys, session)
        aggregated_repeats = defaultdict(lambda: {"volume": 0, "total_users": total_users})
        for step, events in repeated_events_by_journey.items():
            for element_details, url, _ in events:
                aggregated_repeats[(element_details, url)]["volume"] += 1

        for (element_details, url), data in aggregated_repeats.items():
            upsert_journey_friction(
                session, str(journey_id), "repeated", url, element_details,
                FrictionType.REPEATED, (data["volume"] / total_users) * 100,
                total_users, data["volume"]
            )

        # 📉 DROP-OFF events (for JourneyFriction)
        _, _, drop_off_events = calculate_drop_off_distribution(customer_journeys, session)
        drop_off_counts = defaultdict(int)
        for element_details, url in drop_off_events:
            drop_off_counts[(element_details, url)] += 1

        for (element_details, url), volume in drop_off_counts.items():
            upsert_journey_friction(
                session, str(journey_id), "drop_off", url, element_details,
                FrictionType.DROP_OFF, (volume / total_users) * 100,
                total_users, volume
            )

        # 🧠 Generate full step insights funnel JSON
        ideal_path = get_admin_path_for_journey(session, journey_id)
        direct_completed = [j for j in completed_journeys if j.completion_type == CompletionType.DIRECT]
        completed_sequences = [get_event_sequence_for_customer(session, j) for j in direct_completed]
        step_insights = generate_step_insights_from_ideal_path(
            ideal_path_steps=ideal_path,
            completed_journeys=completed_sequences,
            threshold=3
        )

        # 📊 Store journey analytics including step_insights
        insert_journey_analytics(
            session=session,
            journey_id=str(journey_id),
            completion_rate=completion_rate,
            total_completions=total_completions,
            indirect_rate=0,
            completion_time_ms=completion_time,
            steps_completed=0,
            total_steps=0,
            drop_off_distribution={},  # already saved above if needed separately
            slowest_step=0,
            friction_score=0,
            frequent_alt_paths={},
            step_insights=step_insights
        )

    return completion_rates





