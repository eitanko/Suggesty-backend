from sqlalchemy.orm import Session
from models import RawEvent, Event, Journey, CustomerJourney, JourneyLiveStatus, JourneyStatusEnum, Account
from models.customer_journey import CompletionType
from utils import compare_elements  # a custom function to check if two element chains are equivalent
import pandas as pd
import json


# Function to process raw events and update customer journeys
def process_raw_events(session: Session):

    any_changes_made = False

    # STEP 1 — LOAD RAW EVENTS

    # First, we want to collect all raw events that haven’t been processed yet.
    # These are events that were recorded but haven’t been analyzed or assigned to any journey.
    unprocessed_raw_events = session.query(RawEvent).filter_by(processed_ideal_path=False).order_by(RawEvent.timestamp).all()

    # We use pandas here to make it easier to loop over and work with the data.
    # This creates a DataFrame (like an Excel table) where each row is an event.
    # We are extracting only the relevant fields from each event object and keeping a reference to the original SQLAlchemy object (raw_event_obj) so we can update it later.
    raw_events_df = pd.DataFrame([{
        'id': event.id,
        'distinct_id': event.distinct_id,  # user ID
        'url': event.current_url,  # page the event occurred on
        'elements_chain': event.elements_chain,  # DOM path of the clicked element
        'timestamp': event.timestamp,  # when it happened
        'raw_event_obj': event  # actual object we'll update later
    } for event in unprocessed_raw_events])

    # STEP 2 — LOAD IDEAL JOURNEYS

    # We now fetch all active "ideal journeys".
    # An ideal journey represents the desired user flow — like a success path that users should ideally follow.
    # These are used as templates to compare against user behavior.
    active_ideal_journeys = session.query(Journey).filter_by(status=JourneyLiveStatus.ACTIVE).all()

    # Convert the list of ideal journey objects to a DataFrame for easier iteration.
    # Each row will contain the journey’s ID, its first step, its full step list, and how many total steps it has.
    # We're storing all of that in a structured table to efficiently loop through it and make comparisons.
    ideal_journeys_df = pd.DataFrame([{
        'journey_id': journey.id,
        'first_step': journey.first_step,  # a dict with 'url' and 'elements_chain'
        'steps': journey.steps,  # full list of all steps in the journey
        'total_steps': len(journey.steps)  # so we know when a journey is complete
    } for journey in active_ideal_journeys])

    # STEP 3 — PROCESS EACH RAW EVENT

    from collections import defaultdict
    cj_took_extra_steps = defaultdict(bool) # to monitor indirect success
    cj_seen_elements = defaultdict(set)

    # Now we iterate through each raw event that hasn't been processed yet.
    # For each event, we'll first check if it matches the beginning of any ideal journey
    # Then we'll also check if this user is currently in the middle of a journey and whether the event is a next step.
    for index, raw_event_row in raw_events_df.iterrows():
        # Accessing the original event object, and the values we need to compare
        raw_event = raw_event_row['raw_event_obj']
        event_distinct_id = raw_event_row['distinct_id']
        event_url = raw_event_row['url']
        event_elements_chain = raw_event_row['elements_chain']

        event_handled = False  # flag to track if this event has been processed in 3.1 or 3.3

        # STEP 3.1 — CHECK IF THIS EVENT IS THE START OF A NEW JOURNEY

        for journey_index, journey_row in ideal_journeys_df.iterrows():
            journey_id = journey_row['journey_id']
            first_step = journey_row['first_step']  # No json.loads() needed

            # Skip if the user already has an active CustomerJourney for this template
            existing_cj = session.query(CustomerJourney).filter_by(
                person_id=event_distinct_id,
                journey_id=journey_id,
                status=JourneyStatusEnum.IN_PROGRESS
            ).first()

            if existing_cj:
                # print( f"[INFO] Skipping new CJ — user {event_distinct_id} already has an active journey {existing_cj.id} for template {journey_id}")
                continue  # Don’t process this event further

            # Match event with first step of the ideal journey
            first_step_url = first_step.get("url")
            first_step_elements_chain = first_step.get("elementsChain")

            # Check if the url and elements_chain match the first step of the ideal journey
            if first_step_url == event_url and compare_elements(first_step_elements_chain, event_elements_chain):
                # Match found — start a new CustomerJourney
                new_customer_journey = CustomerJourney(
                    session_id=raw_event.session_id,
                    person_id=event_distinct_id,
                    journey_id=journey_id,
                    current_step_index=1,
                    status=JourneyStatusEnum.IN_PROGRESS,
                    start_time=raw_event.timestamp,
                    end_time=raw_event.timestamp,
                    total_steps=journey_row['total_steps']
                )

                session.add(new_customer_journey)
                session.flush()  # Assign ID to `new_customer_journey`

                # Link raw_event to this journey
                raw_event.customer_journey_id = new_customer_journey.id
                raw_event.account_id = 1

                # Create and link the first event (match = True)
                event = Event(
                    person_id=raw_event.distinct_id,
                    page_title="",  # Can be filled later if needed
                    element="",  # Same here
                    event_type=raw_event.event_type,
                    elements_chain=raw_event.elements_chain,
                    url=raw_event.current_url,
                    customer_journey_id=new_customer_journey.id,
                    session_id=raw_event.session_id,
                    timestamp=raw_event.timestamp,
                    is_match=True
                )
                session.add(event)

                # print(
                    # f"[INFO] Created new CustomerJourney for user {event_distinct_id} with journey template {journey_id} at event {raw_event.id}")
                event_handled = True  # mark event as handled (if not handled means we can ignore it)
                continue  # check if this event matches any other journeys

        # If event was already handled in 3.1 (new journey started), skip processing it again in 3.2/3.3
        if event_handled:
            raw_event.processed_ideal_path = True
            any_changes_made = True
            # print(f"[INFO] Skipping 3.2 and 3.3 — event {raw_event.id} already processed in 3.1")
            continue

        # STEP 3.2 — CHECK IF THIS USER IS ALREADY IN A JOURNEY

        # If the user already has one or more in-progress journeys, we want to try to match this event to the next expected step.
        active_cjs_for_user = session.query(CustomerJourney).filter_by(
            person_id=event_distinct_id,
            status=JourneyStatusEnum.IN_PROGRESS
        ).all()

        # we need to make sure that if we inserted a new event in 3.1 we don't process it again in 3.2
        # ✅ Early exit: if the user has no active CJs, No existing journey and didn't start a new one — skip further processing
        if not active_cjs_for_user and not event_handled:
            #and event.customer_journey_id not in [cj.journey_id for cj in active_cjs_for_user]:
            # print(f"[INFO] Skipping event {raw_event.id} — not part of any journey")
            raw_event.processed_ideal_path = True
            any_changes_made = True
            continue  # Skip to next raw event

        # STEP 3.3 — SEE IF THIS EVENT MATCHES THE NEXT STEP IN ANY OF THOSE JOURNEYS

        for cj in active_cjs_for_user:
            # Fetch the ideal journey that this CustomerJourney is based on
            ideal_journey = next((j for j in active_ideal_journeys if j.id == cj.journey_id), None)
            if not ideal_journey:
                continue  # safety check, shouldn't happen

            took_extra_steps = False

            # We need to check if the current step index is within the bounds of the ideal journey
            if cj.current_step_index >= len(ideal_journey.steps):
                continue  # Skip if all steps are already completed

            # Fetch the next expected step in the journey
            expected_step = ideal_journey.steps[cj.current_step_index]

            # Compare the current event with the expected step
            is_match = expected_step.url == event_url and compare_elements(expected_step.elements_chain,
                                                                           event_elements_chain)

            # Create the event
            event = Event(
                person_id=raw_event.distinct_id,
                page_title="",
                element="",
                event_type=raw_event.event_type,
                elements_chain=raw_event.elements_chain,
                url=raw_event.current_url,
                customer_journey_id=cj.id,
                session_id=raw_event.session_id,
                timestamp=raw_event.timestamp,
                is_match=is_match
            )
            session.add(event)

            if is_match:
                cj_seen_elements[cj.id].add((event_url, event_elements_chain))
            else:
                # Mark as extra step only if this unmatched event was not a previously matched one
                if (event_url, event_elements_chain) not in cj_seen_elements[cj.id]:
                    cj_took_extra_steps[cj.id] = True

            # If the event matches, update the journey state
            if is_match:
                if cj.current_step_index == len(ideal_journey.steps) - 1:
                    cj.status = JourneyStatusEnum.COMPLETED
                    cj.current_step_index += 1  # Increment the step index to reflect the final step
                    cj.end_time = raw_event.timestamp  # Update end_time when journey is completed
                    cj.completion_type = CompletionType.DIRECT if not cj_took_extra_steps[cj.id] else CompletionType.INDIRECT

                    # print(f"[INFO] Journey {cj.id} marked as {cj.completion_type}")
                else:
                    cj.current_step_index += 1
                    # print(f"[INFO] Updated CJ {cj.id}: moved to step {cj.current_step_index}")

                session.add(cj)

            # print(f"[INFO] Added {'MATCHED' if is_match else 'UNMATCHED'} event {raw_event.id} to journey {cj.id}")

            continue  # check if this event matches any other journeys

        # At the end of 3.3, if not yet marked:
        if not raw_event.processed_ideal_path:
            raw_event.processed_ideal_path = True
            raw_event.account_id = 1
            any_changes_made = True
            # print(f"[INFO] Marked raw event {raw_event.id} as processed")

        # STEP 4 — MARK EVENT AS PROCESSED

        # After trying to match the event to a journey (either start or in-progress),
        # we mark it as processed so we don’t re-analyze it next time
        # if the event was handled in 3.1 we skip marking it as processed
        if event_handled:
            raw_event.processed_ideal_path = True
            any_changes_made = True
            # print(f"[INFO] Marked raw event {raw_event.id} as processed")
            continue  # skip to next raw event

        # print(f"[INFO] Marked raw event {raw_event.id} as processed")

    # STEP 5 — SAVE EVERYTHING TO DATABASE

    # Commit all the changes we made in this script:
    # - New customer journeys that were created
    # - Existing journeys that were updated
    # - Raw events that were marked as processed

    if any_changes_made:
        session.commit()
        print("[SUCCESS] All raw events were successfully analyzed and saved.")
    else:
        print("[INFO] No new events to process.")
