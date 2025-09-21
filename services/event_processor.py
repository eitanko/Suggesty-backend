from sqlalchemy.orm import Session
from models import RawEvent, Event, Journey, CustomerJourney, JourneyLiveStatus, JourneyStatusEnum, Account
from models.customer_journey import CompletionType
from utils import compare_elements, urls_match_pattern  # Import URL utilities
import pandas as pd
import json


# Function to process raw events and update customer journeys
def process_raw_events(session: Session, account_id: int = None):
    """
    Process raw events.
    If account_id is given, only process events for that account.
    Otherwise, process all unprocessed events.
    """

    any_changes_made = False

    # STEP 1 — LOAD RAW EVENTS

    # First, we want to collect all raw events that haven’t been processed yet.
    # These are events that were recorded but haven’t been analyzed or assigned to any journey.

    query = session.query(RawEvent).filter_by(processed_ideal_path=False)

    if account_id: query = query.filter(RawEvent.account_id == account_id)
    
    unprocessed_raw_events = query.order_by(RawEvent.timestamp).all()

    # We use pandas here to make it easier to loop over and work with the data.
    # This creates a DataFrame (like an Excel table) where each row is an event.
    # We are extracting only the relevant fields from each event object and keeping a reference to the original SQLAlchemy object (raw_event_obj) so we can update it later.
    raw_events_df = pd.DataFrame([{
        'id': event.id,
        'distinct_id': event.distinct_id,  # user ID
        'url': event.current_url,  # page the event occurred on
        'elements_chain': event.elements_chain,  # DOM path of the clicked element
        'x_path': event.x_path,  # XPath of the clicked element (already stored)
        'timestamp': event.timestamp,  # when it happened
        'raw_event_obj': event  # actual object we'll update later
    } for event in unprocessed_raw_events])

    print(f"[DEBUG] Found {len(unprocessed_raw_events)} unprocessed raw events for account {account_id or 'ALL'}")

    # STEP 2 — LOAD IDEAL JOURNEYS

    # We now fetch all active "ideal journeys".
    # An ideal journey represents the desired user flow — like a success path that users should ideally follow.
    # These are used as templates to compare against user behavior.
    active_ideal_journeys = session.query(Journey).filter_by(status=JourneyLiveStatus.ACTIVE).all()

    # Sort steps by creation time for each journey to ensure proper order
    for journey in active_ideal_journeys:
        journey.steps = sorted(journey.steps, key=lambda step: step.created_at)

    
    # Convert the list of ideal journey objects to a DataFrame for easier iteration.
    # Each row will contain the journey’s ID, its first step, its full step list, and how many total steps it has.
    # We're storing all of that in a structured table to efficiently loop through it and make comparisons.
    ideal_journeys_df = pd.DataFrame([{
        'journey_id': journey.id,
        'first_step': journey.first_step,  # a dict with 'url' and 'elements_chain'
        'steps': journey.steps,  # full list of all steps in the journey
        'total_steps': len(journey.steps)  # so we know when a journey is complete
    } for journey in active_ideal_journeys])

    print(f"[DEBUG] Found {len(active_ideal_journeys)} active ideal journeys")

    # STEP 3 — PROCESS EACH RAW EVENT

    from collections import defaultdict
    cj_took_extra_steps = defaultdict(bool) # to monitor indirect success
    cj_seen_elements = defaultdict(set)

    # Now we iterate through each raw event that hasn't been processed yet.
    # For each event, we'll first check if it matches the beginning of any ideal journey
    # Then we'll also check if this user is currently in the middle of a journey and whether the event is a next step.
    
    print(f"[DEBUG] Processing {len(raw_events_df)} raw events against {len(ideal_journeys_df)} ideal journeys")
    
    for index, raw_event_row in raw_events_df.iterrows():
        # Accessing the original event object, and the values we need to compare
        raw_event = raw_event_row['raw_event_obj']
        event_distinct_id = raw_event_row['distinct_id']
        event_url = raw_event_row['url']
        event_elements_chain = raw_event_row['elements_chain']
        event_xpath = raw_event_row['x_path']  # Use stored XPath from RawEvent

        # print(f"\n[DEBUG] Processing event {raw_event.id}:")
        # print(f"  User: {event_distinct_id}")
        # print(f"  URL: {event_url}")
        # print(f"  Event Type: {raw_event.event_type}")
        # # print(f"  Elements chain: {event_elements_chain}")
        # print(f"  XPath: {event_xpath}")

        # Skip pageview and pageleave events - they don't participate in journey matching
        if raw_event.event_type in ['pageview', 'pageleave', 'change', 'submit']:
            print(f"[INFO] Skipping {raw_event.event_type} event - not part of journey matching")
            raw_event.processed_ideal_path = True
            any_changes_made = True
            continue

        event_handled = False  # flag to track if this event has been processed in 3.1 or 3.3

        # STEP 3.1 — CHECK IF THIS EVENT IS THE START OF A NEW JOURNEY

        for journey_index, journey_row in ideal_journeys_df.iterrows():
            journey_id = journey_row['journey_id']
            first_step = journey_row['first_step'] 

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
            first_step = journey_row['first_step']
            
            # Debug: Let's see what we're working with
            # print(f"[DEBUG] Raw first_step type: {type(first_step)}")
            # print(f"[DEBUG] Raw first_step value: {first_step}")
            
            # Parse the JSON string and extract what we need
            try:
                # Just parse the JSON directly - no need to strip quotes now
                parsed_step = json.loads(first_step)
                # print(f"[DEBUG] Successfully parsed - type: {type(parsed_step)}")
            except Exception as e:
                # print(f"[ERROR] JSON parsing failed: {e}")
                # print(f"[ERROR] Raw data: {first_step}")
                continue
                
            first_step_url = parsed_step.get("url")
            first_step_elements_chain = parsed_step.get("elementsChain")
            first_step_xpath = parsed_step.get("xpath")  # Get xpath from stored step data
            
            # URLs are already normalized at entry point, so use directly
            url_match = urls_match_pattern(event_url, first_step_url)
            print(f"  URL match: {url_match}")
            
            # Compare XPath 
            elements_match = False  # Default to False
            if first_step_xpath and event_xpath:
                # Use XPath comparison instead of elements_chain
                elements_match = (first_step_xpath == event_xpath)
                print(f"  XPath comparison: {elements_match}")
            else:
                print(f"  XPath comparison skipped - first_step_xpath: {bool(first_step_xpath)}, event_xpath: {bool(event_xpath)}")
            
            # print(f"  Final elements match: {elements_match}")
            # print(f"  Both URL and elements match: {url_match and elements_match}")

            # Check if BOTH the url and elements_chain match
            if url_match and elements_match:
                print(f"[DEBUG] ✅ MATCH FOUND! Creating new CustomerJourney for journey {journey_id}")
                # Match found — start a new CustomerJourney
                new_customer_journey = CustomerJourney(
                    session_id=raw_event.session_id,
                    person_id=event_distinct_id,
                    journey_id=journey_id,
                    current_step_index=0,  # Start at 0, will be incremented to 1 after first match
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
                    x_path=raw_event.x_path,  # Use stored XPath from RawEvent
                    url=raw_event.current_url,  # URL already normalized at entry point
                    customer_journey_id=new_customer_journey.id,
                    session_id=raw_event.session_id,
                    timestamp=raw_event.timestamp,
                    is_match=True
                )
                session.add(event)

                # Increment step index after successful first match
                new_customer_journey.current_step_index = 1
                session.add(new_customer_journey)

                print(f"[INFO] Created new CustomerJourney {new_customer_journey.id} for user {event_distinct_id} with journey template {journey_id} at event {raw_event.id}")
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

        print(f"[DEBUG] Step 3.3: Checking {len(active_cjs_for_user)} active journeys for user {event_distinct_id}")

        for cj in active_cjs_for_user:
            print(f"[DEBUG] Checking CustomerJourney {cj.id} (template {cj.journey_id}) at step {cj.current_step_index}")
            
            # Fetch the ideal journey that this CustomerJourney is based on
            ideal_journey = next((j for j in active_ideal_journeys if j.id == cj.journey_id), None)
            if not ideal_journey:
                print(f"[ERROR] Could not find ideal journey {cj.journey_id}")
                continue  # safety check, shouldn't happen

            # print(f"[DEBUG] Ideal journey {ideal_journey.id} has {len(ideal_journey.steps)} steps total")
            # for i, step in enumerate(ideal_journey.steps):
                # print(f"[DEBUG] Step {i}: URL='{step.url}', XPath='{step.x_path}'")

            # We need to check if the current step index is within the bounds of the ideal journey
            if cj.current_step_index >= len(ideal_journey.steps):
                print(f"[DEBUG] Journey {cj.id} already completed - current step {cj.current_step_index} >= total steps {len(ideal_journey.steps)}")
                continue  # Skip if all steps are already completed

            # URLs are already normalized at entry point, so use directly
            
            # First, check if this event matches the next expected step
            expected_step = ideal_journey.steps[cj.current_step_index]
            print(f"[DEBUG] Expected next step {cj.current_step_index}: URL='{expected_step.url}', XPath='{expected_step.x_path}'")

            url_match = urls_match_pattern(event_url, expected_step.url)
            xpath_match = (expected_step.x_path and event_xpath and expected_step.x_path == event_xpath)
            
            is_next_step_match = url_match and xpath_match
            print(f"[DEBUG] Next step match: {is_next_step_match} (URL: {url_match}, XPath: {xpath_match})")
            
            # If it doesn't match the next expected step, check if it matches any later step (for indirect completion)
            later_step_match = None
            later_step_index = None
            
            if not is_next_step_match:
                print(f"[DEBUG] Checking if event matches any later steps...")
                for i in range(cj.current_step_index + 1, len(ideal_journey.steps)):
                    step = ideal_journey.steps[i]
                    step_url_match = urls_match_pattern(event_url, step.url)
                    step_xpath_match = (step.x_path and event_xpath and step.x_path == event_xpath)
                    
                    if step_url_match and step_xpath_match:
                        later_step_match = step
                        later_step_index = i
                        print(f"[DEBUG] Found match with later step {i}: URL='{step.url}', XPath='{step.x_path}'")
                        break
            
            # Determine the match result
            if is_next_step_match:
                is_match = True
                matched_step_index = cj.current_step_index
                print(f"[DEBUG] Event matches expected next step {matched_step_index}")
            elif later_step_match:
                is_match = True
                matched_step_index = later_step_index
                cj_took_extra_steps[cj.id] = True  # Mark as indirect since steps were skipped
                print(f"[DEBUG] Event matches later step {matched_step_index} - marking as indirect completion")
            else:
                is_match = False
                print(f"[DEBUG] Event does not match any remaining steps in the journey")

            # Create the event
            event = Event(
                person_id=raw_event.distinct_id,
                page_title="",
                element="",
                event_type=raw_event.event_type,
                elements_chain=raw_event.elements_chain,
                x_path=raw_event.x_path,  # Use stored XPath from RawEvent
                url=raw_event.current_url,  # URL already normalized at entry point
                customer_journey_id=cj.id,
                session_id=raw_event.session_id,
                timestamp=raw_event.timestamp,
                is_match=is_match
            )
            session.add(event)
            print(f"[DEBUG] Created Event with is_match={is_match} for CustomerJourney {cj.id}")

            # If the event matches, update the journey state
            if is_match:
                print(f"[DEBUG] Event matched step {matched_step_index}! Updating journey state...")
                
                # Track using XPath if available, otherwise use elements_chain
                tracking_key = event_xpath if event_xpath else event_elements_chain
                cj_seen_elements[cj.id].add((event_url, tracking_key))
                
                # If we matched the next expected step, advance normally
                if is_next_step_match:
                    cj.current_step_index += 1
                    print(f"[DEBUG] Advanced to next step: {cj.current_step_index}")
                else:
                    # If we matched a later step, advance to that step + 1
                    cj.current_step_index = matched_step_index + 1
                    print(f"[DEBUG] Jumped to step {matched_step_index}, now at: {cj.current_step_index}")
                
                # Check if journey is completed
                if cj.current_step_index >= len(ideal_journey.steps):
                    cj.status = JourneyStatusEnum.COMPLETED
                    cj.end_time = raw_event.timestamp
                    cj.completion_type = CompletionType.DIRECT if not cj_took_extra_steps[cj.id] else CompletionType.INDIRECT
                    print(f"[INFO] Journey {cj.id} COMPLETED as {cj.completion_type}")
                else:
                    print(f"[INFO] Journey {cj.id} progress: {cj.current_step_index}/{len(ideal_journey.steps)} steps completed")

                session.add(cj)
            else:
                print(f"[DEBUG] Event did not match any step - marking as extra step")
                # Mark as extra step only if this unmatched event was not a previously matched one
                tracking_key = event_xpath if event_xpath else event_elements_chain
                if (event_url, tracking_key) not in cj_seen_elements[cj.id]:
                    cj_took_extra_steps[cj.id] = True

            print(f"[INFO] Added {'MATCHED' if is_match else 'UNMATCHED'} event {raw_event.id} to journey {cj.id}")

            # Important: Break after processing this event against this journey
            # Each event should only be processed against one active journey per user
            break

                # Mark all events as processed at the end of each iteration
        raw_event.processed_ideal_path = True
        raw_event.account_id = 1
        any_changes_made = True


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
