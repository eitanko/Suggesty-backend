from models.customer_journey import Person, CustomerJourney, JourneyStatusEnum, Event, Journey, CustomerSession, Step
from flask import Blueprint, request, jsonify
from db import db
from datetime import datetime
import json

# Create a Blueprint for events
event_blueprint = Blueprint('event', __name__)

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
    session = CustomerSession.query.filter_by(session_id=session_id).first()

    if not person or not session:
        print("❌ Person or session not found")
        return jsonify({"error": "Person or session not found"}), 404

    print(f"✅ Found Person: {person}, Found Session: {session}")

    # Check if there is an ongoing journey (status = "IN_PROGRESS")
    ongoing_journey = CustomerJourney.query.filter_by(person_id=person.uuid, status="IN_PROGRESS").first()

    if ongoing_journey:
        print(f"✅ Ongoing journey found: {ongoing_journey.id}")

        element_str = json.dumps(element) if isinstance(element, dict) else element

        # If a journey is ongoing, insert the event with CJID
        new_event = Event(
            session_id=session_id,
            event_type=event_type,
            url=current_url,
            element=element_str,
            customer_journey_id=ongoing_journey.id,
            timestamp=datetime.utcnow(),
            person_id = person.uuid
        )
        db.session.add(new_event)
        db.session.commit()

        print(f"✅ Event tracked for ongoing journey: {ongoing_journey.id}")
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
        # Ensure element is a JSON string if it's a dictionary
        element_str = json.dumps(element) if isinstance(element, dict) else element

        first_event = Event(
            session_id=session_id,
            event_type=event_type,
            url=current_url,
            element=element_str,
            customer_journey_id=new_journey.id,
            timestamp=datetime.utcnow(),
            person_id = person.uuid
        )
        db.session.add(first_event)
        db.session.commit()

        print(f"✅ First event recorded for new journey: {new_journey.id}")
        return jsonify({"status": "New journey started and event tracked", "CJID": new_journey.id}), 201
    else:
        print("❌ Invalid journey start or element interaction.")
        return jsonify({"error": "Invalid journey start or element interaction."}), 400
