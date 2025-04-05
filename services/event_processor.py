import json
from db import db
from models import RawEvent, CustomerJourney, Event, Journey, JourneyLiveStatus  # Your SQLAlchemy models
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import uuid
from utils.norm_and_compare import compare_elements


def process_raw_events(session: Session):
    # 1. Fetch journeys with firstStep info
    journeys = session.query(Journey).filter(Journey.first_step.isnot(None)).filter_by(status=JourneyLiveStatus.ACTIVE).all()
    # journeys = Journey.query.with_entities(Journey.first_step, Journey.id).filter_by(status=JourneyLiveStatus.ACTIVE).all()

    journey_start_conditions = []

    for journey in journeys:
        try:
            step_data = json.loads(journey.firstStep)
            journey_start_conditions.append({
                "journey_id": journey.id,
                "url": step_data.get("url"),
                "event_type": step_data.get("eventType"),
                "elements_chain": step_data.get("elementsChain")
            })
        except json.JSONDecodeError:
            print(f"Invalid JSON in journey {journey.id}, skipping...")

    # 2. Group raw events by session
    session_ids = session.query(RawEvent.session_id).distinct().all()

    for (session_id,) in session_ids:
        raw_events = session.query(RawEvent).filter_by(session_id=session_id).order_by(RawEvent.timestamp).all()
        if not raw_events:
            continue

        raw_event = raw_events[0]
        matched_journey = None

        # 3. Try to find a matching journey by first step
        for ideal_journey in journey_start_conditions:
            if (
                raw_event.pathname == ideal_journey["url"] and
                raw_event.eventType == ideal_journey["event_type"] and
                compare_elements(ideal_journey["elements_chain"],raw_event.elementsChain)
            ):
                matched_journey = ideal_journey["journey_id"]
                break

        if not matched_journey:
            print(f"Session {session_id} does not match any journey, skipping.")
            continue

        # 4. Create CustomerJourney
        journey_uuid = str(uuid.uuid4())
        customer_journey = CustomerJourney(
            id=journey_uuid,
            session_id=session_id,
            distinct_id=raw_event.distinctId,
            started_at=raw_event.timestamp,
            ended_at=raw_events[-1].timestamp,
            total_steps=len(raw_events),
            journey_id=matched_journey
        )
        session.add(customer_journey)
        session.flush()

        # 5. Save associated events
        for index, raw in enumerate(raw_events):
            event = Event(
                customer_journey_id=journey_uuid,
                session_id=raw.session_id,
                distinct_id=raw.distinctId,
                event=raw.event,
                event_type=raw.eventType,
                pathname=raw.pathname,
                current_url=raw.currentUrl,
                elements_chain=raw.elementsChain,
                timestamp=raw.timestamp,
                step_index=index
            )
            session.add(event)

    session.commit()
    print("✅ Done processing raw events.")
