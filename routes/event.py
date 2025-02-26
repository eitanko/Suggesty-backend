from models.customer_journey import Person, CustomerJourney, JourneyStatusEnum, Event, Journey, CustomerSession, Step
from flask import Blueprint, request, jsonify, session
from db import db
from datetime import datetime
import json

# Create a Blueprint for events
event_blueprint = Blueprint('event', __name__)

def insert_event_and_update_journey(session_id, event_type, current_url, element, person_uuid, ongoing_journey=None, new_journey=None):
    """
    Helper function to insert an event and update the customer journey's updatedAt timestamp.
    This function will handle inserting both new events and marking the journey as completed.
    """
    element_str = json.dumps(element) if isinstance(element, dict) else element
    event = Event(
        session_id=session_id,
        event_type=event_type,
        url=current_url,
        element=element_str,
        customer_journey_id=(ongoing_journey.id if ongoing_journey else new_journey.id),
        timestamp=datetime.utcnow(),
        person_id=person_uuid
    )
    db.session.add(event)

    # Update the `updatedAt` timestamp for the customer journey
    if ongoing_journey:
        ongoing_journey.updatedAt = datetime.utcnow()
        db.session.commit()
        print(f"✅ Event tracked for ongoing journey: {ongoing_journey.id}")
    elif new_journey:
        new_journey.updatedAt = datetime.utcnow()
        db.session.commit()
        print(f"✅ Event tracked for new journey: {new_journey.id}")

    db.session.commit()
    return event

@event_blueprint.route("/track", methods=["POST"])
def track_event():
    """
    Track user events for ongoing or new customer journeys.

    Request Body:
    - uuid: The unique identifier for the user.
    - sessionId: The session ID associated with the user.
    - url: The current URL the user is on.
    - elementDetails: The details of the element the user interacted with (xpath, action).

    Response:
    - JSON containing the result of the event tracking.
    """
    print("🔹 Received a track event request")

    data = request.get_json()
    print(f"🔹 Request Data: {data}")

    person_id = data.get("uuid")
    session_id = data.get("sessionId")
    current_url = data.get("url")
    event_type = data.get("eventType")
    element = data.get("element")
    xpath = element.get("xpath") if element else None

    print(f"🔹 Extracted Values: Person ID: {person_id}, Session ID: {session_id}, URL: {current_url}, Event Type: {event_type}, XPath: {xpath}")

    # Retrieve the person and session
    person = Person.query.filter_by(uuid=person_id).first()
    customer_session = CustomerSession.query.filter_by(session_id=session_id).first()

    if not person or not customer_session:
        print("❌ Person or customer_session not found")
        return jsonify({"error": "Person or customer_session not found"}), 404

    print(f"✅ Found Person: {person}, Found customer_session: {customer_session}")

    # Check if there is an ongoing journey (status = "IN_PROGRESS")
    ongoing_journey = CustomerJourney.query.filter_by(person_id=person.uuid, status="IN_PROGRESS").first()

    if ongoing_journey:
        print(f"✅ Ongoing journey found: {ongoing_journey.id}")

        if 'journey_steps' not in session:
            # Fetch journey steps from the database
            print(f"Fetching steps for journey_id: {ongoing_journey.journey_id}")
            journey_steps = Step.query.filter_by(journey_id=ongoing_journey.journey_id).order_by(Step.created_at).all()
            session['journey_steps'] = [{'step_number': i+1, 'url': step.url, 'xpath': json.loads(step.element).get('xpath'), 'completed': False} for i, step in enumerate(journey_steps)]
            print(f"Stored journey steps in session: {session['journey_steps']}")

        # Load journey steps from session
        journey_steps = session['journey_steps']
        print(f"Loaded journey steps from session: {journey_steps}")

        # Check if the current event matches the next step in the journey
        for step in journey_steps:
            print("step['url'] ",step['url']," current_url ",current_url," step['xpath'] '",step['xpath'],"' xpath '",xpath,"'")
            if step['url'] == current_url and xpath.strip() == step['xpath'].strip():
                step['completed'] = True
                break

        # Update the journey steps in the session
        session['journey_steps'] = journey_steps
        print(f"Updated journey steps in session: {session['journey_steps']}")

        # Check if all steps are completed
        if all(step['completed'] for step in journey_steps):
            print("All steps completed! Marking journey as COMPLETED")
            ongoing_journey.status = "COMPLETED"
            ongoing_journey.completed_at = datetime.utcnow()
            db.session.commit()

            print(f"Journey {ongoing_journey.id} marked as COMPLETED at {ongoing_journey.completed_at}")

            # Insert a final "completion" event when the journey is completed
            insert_event_and_update_journey(session_id, event_type, current_url, element, person.uuid, ongoing_journey=ongoing_journey)

            # Respond with journey completion
            return jsonify({"status": "Journey completed", "CJID": ongoing_journey.id}), 200

        # Insert event for ongoing journey
        insert_event_and_update_journey(session_id, event_type, current_url, element, person.uuid, ongoing_journey=ongoing_journey)
        return jsonify({"status": "Event tracked", "CJID": ongoing_journey.id}), 200

    print("🔹 No ongoing journey found. Looking for a journey start point...")

    # Fetch the first Step and its Journey ID related to the current URL by sorting by created_at
    first_step = Step.query.join(Journey).filter(
        Journey.start_url == current_url  # Ensure it's the valid journey start point
    ).order_by(Step.created_at).with_entities(Step, Journey.id).first()

    if first_step is None:
        print("ℹ️ No journey found for this URL. Skipping journey tracking.")
        return jsonify({"status": "No journey found for this URL. Event not tracked."}), 200

    step, journey_id = first_step  # Unpack tuple (Step object, Journey ID)
    print(f"✅ Found first step id: {step.id}, Element: {step.element}")

    if xpath and xpath in step.element:  # Check if xpath is contained in the element string
        print("✅ XPath matches first step's element, starting new journey.")

        session.clear()

        # Create a new journey and track the first event
        new_journey = CustomerJourney(
            session_id=session_id,
            journey_id=journey_id,
            person_id=person.uuid,
            status=JourneyStatusEnum.IN_PROGRESS.value,  # Use the enum value for "in-progress"
        )

        db.session.add(new_journey)
        db.session.commit()

        print(f"✅ New journey created with ID: {new_journey.id}")

        # Fetch journey steps from the database and store them in the session
        journey_steps = Step.query.filter_by(journey_id=journey_id).order_by(Step.created_at).all()
        session['journey_steps'] = [{'step_number': i+1, 'url': step.url, 'xpath': json.loads(step.element).get('xpath'), 'completed': False} for i, step in enumerate(journey_steps)]
        print(f"Stored journey steps in session: {session['journey_steps']}")

        # Insert the first event and update the journey's updatedAt timestamp
        insert_event_and_update_journey(session_id, event_type, current_url, element, person.uuid, new_journey=new_journey)

        print(f"✅ First event recorded for new journey: {new_journey.id}")
        return jsonify({"status": "New journey started and event tracked", "CJID": new_journey.id}), 201
    else:
        print("❌ Invalid journey start or element interaction.")
        return jsonify({"error": "Invalid journey start or element interaction."}), 400