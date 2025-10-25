from collections import defaultdict
from sqlalchemy.orm import Session
from models import JourneyStatusEnum, CompletionType
from repositories.journeys import fetch_journeys, group_customer_journeys_by_journey_id
from repositories.events import fetch_steps_for_journey
from repositories.analytics import upsert_journey_analytics
from repositories.friction import upsert_friction
from calculators.completion import (
    calculate_completion_rate, calculate_completed_journeys, calculate_completion_times
)
from calculators.indirect import (
    calculate_indirect_completion_rate, extract_frequent_alternatives
)
from calculators.repeats import calculate_repeated_behavior_all_journeys
from calculators.dropoffs import calculate_drop_off_distribution
from calculators.insights import generate_step_insights_from_ideal_path
from models.customer_journey import FrictionType

def get_event_sequence_for_customer(session, journey):
    # keep your original; consider moving to repositories/events later
    from models import Event
    events = (session.query(Event)
              .filter(Event.customer_journey_id == journey.id)
              .order_by(Event.timestamp).all())
    return [{
        "url": e.url,
        "element": e.elements_chain,
        "xPath": e.x_path,
        "timestamp": int(e.timestamp.timestamp() * 1000),
        "is_match": e.is_match,
        "session_id": e.session_id,
        "event_id": e.id
    } for e in events]

def get_admin_path_for_journey(session, journey_id: int):
    steps = fetch_steps_for_journey(session, journey_id)
    return [{
        "step": s.index,
        "name": s.name,
        "url": s.url,
        "element": s.elements_chain,
        "xPath": s.x_path,
        "timestamp": s.created_at
    } for s in steps]

def process_journey_metrics(session: Session, account_id: int):
    journeys = fetch_journeys(session, account_id)
    if not journeys:
        print(f"[DEBUG] No journeys found for account {account_id or 'ALL'}")
        return {}

    journey_groups = group_customer_journeys_by_journey_id(journeys)

    if account_id is None:
        account_id = journeys[0].account_id

    # 2) Aggregate metrics
    completion_rates = calculate_completion_rate(journey_groups)
    total_completed   = calculate_completed_journeys(journey_groups)
    completion_times  = calculate_completion_times(journey_groups)
    indirect_rates    = calculate_indirect_completion_rate(journey_groups)

    # 3) Per journey
    for journey_id, customer_journeys in journey_groups.items():
        completed_journeys = [j for j in customer_journeys if j.status == JourneyStatusEnum.COMPLETED]
        total_users        = len(customer_journeys)
        total_completions  = total_completed.get(journey_id, 0)
        completion_rate    = completion_rates.get(journey_id, 0)
        completion_time    = completion_times.get(journey_id, 0)
        indirect_rate      = indirect_rates.get(journey_id, 0)

        # repeated
        repeated_events_by_journey = calculate_repeated_behavior_all_journeys(customer_journeys, session)
        aggregated_repeats = defaultdict(lambda: {"volume": 0, "total_users": total_users})
        for _, events in repeated_events_by_journey.items():
            for element_details, url, session_id, _ in events:
                aggregated_repeats[(element_details, url, session_id)]["volume"] += 1

        for (element_details, url, session_id), data in aggregated_repeats.items():
            upsert_friction(
                session,
                journey_id=str(journey_id),
                event_name="repeated",
                url=url,
                event_details=element_details,
                session_id=session_id,
                friction_type=FrictionType.REPEATED,
                friction_rate=(data["volume"] / total_users) * 100 if total_users else 0,
                total_users=total_users,
                volume=data["volume"],
                account_id=account_id,
            )

        # drop-offs
        ideal_path = get_admin_path_for_journey(session, journey_id)
        _, _, drop_off_events = calculate_drop_off_distribution(customer_journeys, session, ideal_path)
        drop_off_counts = defaultdict(int)
        for element_details, url, session_id in drop_off_events:
            drop_off_counts[(element_details, url, session_id)] += 1

        for (element_details, url, session_id), volume in drop_off_counts.items():
            upsert_friction(
                session,
                journey_id=str(journey_id),
                event_name="drop_off",
                url=url,
                event_details=element_details,
                session_id=session_id,
                friction_type=FrictionType.DROP_OFF,
                friction_rate=(volume / total_users) * 100 if total_users else 0,
                total_users=total_users,
                volume=volume,
                account_id=account_id,
            )

        # insights
        direct_completed = [j for j in completed_journeys if j.completion_type == CompletionType.DIRECT]
        completed_sequences = [
            seq for j in direct_completed if (seq := get_event_sequence_for_customer(session, j))
        ]

        step_insights, delayed_events = generate_step_insights_from_ideal_path(
            ideal_path_steps=ideal_path,
            completed_journeys=completed_sequences,
            threshold=10,
            repeated_events={(ed, url): data["volume"] / total_users if total_users else 0
                             for (ed, url, _sid), data in aggregated_repeats.items()},
            drop_off_events={(ed, url): volume / total_users if total_users else 0
                             for (ed, url, _sid), volume in drop_off_counts.items()}
        )

        for element_details, url, session_id, delay_ms in delayed_events:
            upsert_friction(
                session=session,
                journey_id=str(journey_id),
                event_name="delay",
                url=url,
                event_details=element_details,
                session_id=session_id,
                friction_type=FrictionType.DELAY,
                friction_rate=(delay_ms / total_users) * 100 if total_users else 0,
                total_users=total_users,
                volume=delay_ms,
                account_id=account_id,
            )

        # indirect alt paths
        indirect_completed = [j for j in completed_journeys if j.completion_type == CompletionType.INDIRECT]
        frequent_alt_paths = extract_frequent_alternatives(indirect_completed, session)

        upsert_journey_analytics(
            session=session,
            journey_id=str(journey_id),
            account_id=account_id,
            completion_rate=completion_rate,
            total_completions=total_completions,
            total_users=total_users,
            indirect_rate=indirect_rate,
            completion_time_ms=completion_time,
            total_steps=0,
            drop_off_distribution={},
            friction_score=0,
            frequent_alt_paths=frequent_alt_paths,
            step_insights=step_insights,
        )

    return completion_rates
