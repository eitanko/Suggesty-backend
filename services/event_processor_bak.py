import json
from models import RawEvent, CustomerJourney, Event, Journey, JourneyLiveStatus, \
    JourneyStatusEnum  # Your SQLAlchemy models
from sqlalchemy.orm import Session
from utils.norm_and_compare import compare_elements


# Function to fetch journeys with a first step
def fetch_journeys(session: Session):
    journeys = session.query(Journey).filter(Journey.first_step.isnot(None)).filter_by(status=JourneyLiveStatus.ACTIVE).all()

    journey_start_conditions = []

    for journey in journeys:
        try:
            step_data = json.loads(journey.first_step)
            journey_start_conditions.append({
                "journey_id": journey.id,
                "url": step_data.get("url"),
                "event_type": step_data.get("eventType"),
                "elements_chain": step_data.get("elementsChain"),
                "last_step": journey.last_step  # Track the end step here
            })
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for journey {journey.id}: {str(e)}")
            continue  # Skip this journey and move to the next

    return journey_start_conditions


# Function to group raw events by session
def fetch_raw_events(session: Session):
    distinct_ids = session.query(RawEvent.distinct_id).distinct().all()
    session_events = {}

    for (distinct_id,) in distinct_ids:
        raw_events = session.query(RawEvent).filter_by(distinct_id=distinct_id).order_by(RawEvent.timestamp).all()
        if raw_events:
            session_events[distinct_id] = raw_events
        else:
            print(f"No raw events found for person {distinct_id}. Skipping...")

    return session_events


# Function to find the matching journey based on raw events
def find_matching_journey(raw_events, journey_start_conditions):
    matched_journey = None
    last_step = None

    for raw_event in raw_events:
        for ideal_journey in journey_start_conditions:
            print(f"Checking if raw event matches journey {ideal_journey['journey_id']}...")

            if (
                raw_event.current_url == ideal_journey["url"] and
                raw_event.event_type == ideal_journey["event_type"] and
                compare_elements(ideal_journey["elements_chain"], raw_event.elements_chain)
            ):
                matched_journey = ideal_journey["journey_id"]
                last_step = ideal_journey["last_step"]  # Get the end step
                print(f"Found matching journey {matched_journey} for session {raw_event.distinct_id}.")
                break  # Exit the loop if a match is found
        if matched_journey:
            break

    return matched_journey, last_step


def process_and_add_new_events_to_existing_journey(session: Session, matched_journey, raw_events, customer_journey,
                                                   last_step):
    # Get the timestamp of the last processed event from the CustomerJourney
    last_processed_timestamp = customer_journey.end_time if customer_journey.end_time else customer_journey.start_time

    # Filter the raw events to get only the events that are newer than the last processed timestamp
    new_raw_events = [raw for raw in raw_events if raw.timestamp > last_processed_timestamp]

    if not new_raw_events:
        print(f"No new events to process for session {customer_journey.distinct_id}.")
        return  # No new events to process

    print(f"Processing {len(new_raw_events)} new events for session {customer_journey.distinct_id}...")

    # Now, process only the new events
    for index, raw in enumerate(new_raw_events):
        try:
            print(f"Processing new event {index + 1}/{len(new_raw_events)} for session {raw.distinct_id}...")

            # Create the event object to be added
            event = Event(
                person_id=raw.distinct_id,  # Ensure person_id is set
                customer_journey_id=customer_journey.id,  # Link to the existing CustomerJourney
                session_id=raw.session_id,
                page_title="",  # You can populate this if needed, currently left blank
                element="",  # Not needed with PostHog, can leave empty
                event_type=raw.event_type,
                url=raw.current_url,
                elements_chain=raw.elements_chain,
                timestamp=raw.timestamp,
            )
            session.add(event)

            # Check if the current event matches the end step
            if compare_elements(json.loads(last_step).get("elementsChain"), raw.elements_chain):
                # Update the customer journey as completed
                customer_journey.end_time = raw.timestamp
                customer_journey.status = JourneyStatusEnum.COMPLETED.value
                print(f"Journey {customer_journey.id} completed at step {index + 1}!")
                break  # Stop processing events for this journey since it's completed

        except Exception as e:
            print(f"Error processing event for session {raw.distinct_id} at step {index + 1}: {str(e)}")
            continue  # Continue to the next event if an error occurs

    session.commit()


# Function to check and create a new customer journey
def create_customer_journey(session: Session, matched_journey, raw_events):
    print(f"Creating new customer journey for session {raw_events[0].distinct_id} and journey {matched_journey}...")
    customer_journey = CustomerJourney(
        session_id=raw_events[0].session_id,
        journey_id=matched_journey,
        person_id=raw_events[0].distinct_id,  # Person ID from the first event
        start_time=raw_events[0].timestamp,
        end_time=raw_events[-1].timestamp,  # Last event timestamp
        total_steps=len(raw_events),
    )
    session.add(customer_journey)
    session.flush()  # Ensure the customer journey is flushed to get the id for associating events
    return customer_journey


# Function to process raw events and update customer journeys
def process_raw_events(session: Session):
    # Fetch the active journeys with their first step conditions
    journey_start_conditions = fetch_journeys(session)

    # Group raw events by session
    session_events = fetch_raw_events(session)

    # Loop through sessions and process their events
    for distinct_id, raw_events in session_events.items():
        if not raw_events:
            continue

        print(f"Processing session {distinct_id}...")

        # Find the matching journey for the session
        matched_journey, last_step = find_matching_journey(raw_events, journey_start_conditions)

        if not matched_journey:
            print(f"Person {distinct_id} does not match any journey. Skipping...")
            continue

        # Check if the customer journey already exists for this user
        existing_journey = session.query(CustomerJourney).filter_by(distinct_id=distinct_id,
                                                                    status=JourneyLiveStatus.ACTIVE).first()
        if existing_journey:
            # Handle the case when the journey is active
            print(f"Customer journey for distinct_id {distinct_id} is already active. Adding new events...")
            process_and_add_new_events_to_existing_journey(session, matched_journey, raw_events, existing_journey,
                                                           last_step)
            continue  # Skip creating a new customer journey if it already exists
        # Create a new customer journey if it doesn't exist yet
        customer_journey = create_customer_journey(session, matched_journey, raw_events)

        # Process and associate the events with the customer journey
        for index, raw in enumerate(raw_events):
            try:
                print(f"Processing event {index + 1}/{len(raw_events)} for person {distinct_id}...")

                event = Event(
                    person_id=raw.distinct_id,  # Ensure person_id is set
                    customer_journey_id=customer_journey.id,  # Link to the CustomerJourney
                    session_id=raw.session_id,
                    page_title="",  # You can populate this if needed, currently left blank
                    element="",  # Not needed with PostHog, can leave empty
                    event_type=raw.event_type,
                    url=raw.current_url,
                    elements_chain=raw.elements_chain,
                    timestamp=raw.timestamp,
                )
                session.add(event)

                # Check if the current event matches the end step
                if compare_elements(json.loads(last_step).get("elementsChain"), raw.elements_chain):
                    # Update the customer journey as completed
                    customer_journey.end_time = raw.timestamp
                    customer_journey.status = JourneyStatusEnum.COMPLETED.value
                    print(f"Journey {customer_journey.id} completed at step {index + 1}!")
                    break  # Stop processing events for this journey
            except Exception as e:
                print(f"Error processing event for person {distinct_id} at step {index + 1}: {str(e)}")
                continue  # Continue to the next event if an error occurs

        session.commit()

    print("✅ Done processing raw events.")
