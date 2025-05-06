from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from sqlalchemy.event import Events
from sqlalchemy.orm import Session
from models import CustomerJourney, JourneyAnalytics, JourneyStatusEnum, Event
from models.customer_journey import FrictionType, JourneyFriction


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

def calculate_indirect_completion_rate(analytics):
    completed = [a for a in analytics if a.match_type in ("DIRECT", "INDIRECT")]
    indirect = [a for a in analytics if a.match_type == "INDIRECT"]
    return len(indirect) / len(completed) if completed else 0

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
    drop_off_reasons: dict
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
        journey_analytics.step_insights=drop_off_reasons
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
            drop_off_step=drop_off_distribution,
            slowest_step=slowest_step,
            friction_score=friction_score,
            frequent_alt_paths=frequent_alt_paths,
            step_insights=drop_off_reasons,
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

from utils import compare_elements  # a custom function to check if two element chains are equivalent


def detect_repeated_behavior(session: Session, cj_id: str, last_ideal_step: int, threshold: int = 3) -> List[Tuple[str, str, int]]:
    # Fetch the journey events for the given customer journey ID (ordered by timestamp)
    journey_events = session.query(Event).filter_by(customer_journey_id=cj_id).order_by(Event.timestamp).all()

    # Extract the relevant events starting from the last ideal step onwards
    # Ensure that we do not try to slice the list with a negative index
    start_index = max(0, last_ideal_step - 2)

    # Slice the list safely
    events_after_last_step = journey_events[start_index:]

    # If there are no events after the ideal step, return an empty list
    if not events_after_last_step:
        return []

    # Initialize the current event and previous event for tracking repeated events
    current_event = events_after_last_step[0]  # First event after the last ideal step
    counter = 0  # Initialize counter
    # List to store repeated event information
    repeated_steps = []

    # Iterate over the events after the last ideal step to check for repeated sequences
    for event in events_after_last_step[1:]:
        # Check if the url and elements_chain match the first step of the ideal journey
        if event.url == current_event.url and compare_elements(event.elements_chain, current_event.elements_chain):
        # if event.elements_chain == current_event.elements_chain:
            # If the elements_chain is the same as the first one, increase the counter
            counter += 1
        else:
            # If the sequence is broken, check if the current sequence meets the threshold
            if counter >= threshold:
                repeated_steps.append((current_event.elements_chain.split(';')[0], current_event.url, counter))  # Store the event and count
            # Reset the counter and update the current_event to the new event
            current_event = event
            counter = 1

    # After the loop, check the last sequence
    if counter >= threshold:
        repeated_steps.append((current_event.elements_chain.split(';')[0], current_event.url, counter))

    # If no sequence exceeds the threshold, return an empty list
    return repeated_steps

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
                drop_off_events.append((last_event.elements_chain, last_event.url))

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

from collections import defaultdict

def process_journey_metrics(session: Session):
    """
    Process journey metrics such as completion rate and completion time, and insert the results into JourneyAnalytics table.
    """

    # Fetch customer journeys grouped by journeyId
    journey_groups = fetch_customer_journeys_by_journey_id(session)
    print(f"Fetched {len(journey_groups)} journeys.")

    # Calculate completion rate, total completed journeys, and completion times
    completion_rates = calculate_completion_rate(journey_groups)
    total_completed = calculate_completed_journeys(journey_groups)
    completion_times = calculate_completion_times(journey_groups)

    # Iterate over each journey and insert/update metrics
    for journey_id in journey_groups.keys():

        # Retrieve the relevant metrics for this journey
        completion_rate = completion_rates.get(journey_id, 0)
        completion_time = completion_times.get(journey_id, 0)
        total_completions = total_completed.get(journey_id, 0)

        # Calculate drop-off distribution and reasons (including repeated events)
        drop_off_distribution, drop_off_reasons, drop_off_events = calculate_drop_off_distribution(
            journey_groups[journey_id], session
        )

        print(f"Drop-off distribution for journey {journey_id}: {drop_off_distribution}")

        # 🎯 🔽 START OF FRICTION AGGREGATION BLOCK
        total_users = len(journey_groups[journey_id])  # Total users for this journey
        print(f"Total users for journey {journey_id}: {total_users}")

        repeated_events = drop_off_reasons  # {step: [(element, url, count), ...]}

        # Initialize a dictionary to aggregate repeated events
        aggregated_friction_data = defaultdict(lambda: {"volume": 0, "total_users": 0})

        for step, events in repeated_events.items():  # Loop through each step's repeated events
            for element_details, url, count in events:  # For each repeated event (element, url, count)
                # Accumulate volume for each event (distinct repetitions)
                aggregated_friction_data[(element_details, url)]["volume"] += 1
                # Total users (this is the same for all repetitions of the event)
                aggregated_friction_data[(element_details, url)]["total_users"] = total_users

        # Now calculate the friction rate for each aggregated event
        for (element_details, url), data in aggregated_friction_data.items():
            volume = data["volume"]
            total_users = data["total_users"]
            # Calculate friction rate as the percentage of users who experienced the friction event
            friction_rate = (volume / total_users) * 100  # Percentage of users who had this event

            # Print the aggregated data before upserting (for debugging)
            print(f"Upsert data for event: {element_details}, {url}")
            print(f"Volume: {volume}, Total Users: {total_users}, Friction Rate: {friction_rate}%")

            # Call upsert to insert/update the aggregated friction data into JourneyFriction
            upsert_journey_friction(
                session=session,
                journey_id=str(journey_id),
                event_name="repeated",  # You can refine this if needed
                url=url,
                event_details=element_details,
                friction_type=FrictionType.REPEATED,
                friction_rate=friction_rate,
                total_users=total_users,
                volume=volume
            )
        # 🎯 🔼 END OF FRICTION AGGREGATION BLOCK

        # Insert the journey analytics into JourneyAnalytics table
        insert_journey_analytics(
            session,
            str(journey_id),
            completion_rate,
            total_completions,
            0,  # Placeholder for indirect_rate
            completion_time,
            0,  # Placeholder for steps_completed
            0,  # Placeholder for total_steps
            drop_off_distribution,
            0,  # Placeholder for slowest_step
            0,  # Placeholder for friction_score
            {},  # Placeholder for frequent_alt_paths
            drop_off_reasons  # Drop-off reasons for this journey
        )

    return completion_rates




