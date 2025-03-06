from models.customer_journey import Person, CustomerJourney, JourneyStatusEnum, Event, Journey, CustomerSession, Step, JourneyLiveStatus
from flask import Blueprint, request, jsonify, session
from db import db
from datetime import datetime
import json

# Create a Blueprint for events
event_blueprint = Blueprint('event', __name__)

def fetch_person_and_session(person_id, session_id):
    person = Person.query.filter_by(uuid=person_id).first()
    customer_session = CustomerSession.query.filter_by(session_id=session_id).first()
    return person, customer_session

def handle_ongoing_journey(ongoing_journey, session_id, event_type, current_url, page_title, element, person_uuid):
    if 'journey_steps' not in session:
        journey_steps = fetch_journey_steps(ongoing_journey.journey_id)
        session['journey_steps'] = journey_steps

    journey_steps = session['journey_steps']
    mark_step_completed(journey_steps, current_url, element.get('xpath'))

    if all(step['completed'] for step in journey_steps):
        complete_journey(ongoing_journey)
        insert_event_and_update_journey(session_id, event_type, current_url, page_title, element, person_uuid, ongoing_journey=ongoing_journey)
        return jsonify({"status": "Journey completed", "CJID": ongoing_journey.id}), 200

    insert_event_and_update_journey(session_id, event_type, current_url, page_title, element, person_uuid, ongoing_journey=ongoing_journey)
    return jsonify({"status": "Event tracked", "CJID": ongoing_journey.id}), 200

def start_new_journey(session_id, event_type, current_url, page_title, element, person_uuid, journey_id):
    session.clear()
    new_journey = CustomerJourney(
        session_id=session_id,
        journey_id=journey_id,
        person_id=person_uuid,
        status=JourneyStatusEnum.IN_PROGRESS.value,
    )
    db.session.add(new_journey)
    db.session.commit()

    journey_steps = fetch_journey_steps(journey_id)
    session['journey_steps'] = journey_steps

    mark_step_completed(journey_steps, current_url, element.get('xpath'))
    insert_event_and_update_journey(session_id, event_type, current_url, page_title, element, person_uuid, new_journey=new_journey)
    return jsonify({"status": "New journey started and event tracked", "CJID": new_journey.id}), 201

def fetch_journey_steps(journey_id):
    steps = Step.query.filter_by(journey_id=journey_id).order_by(Step.created_at).all()
    return [{'step_number': i+1, 'url': step.url, 'xpath': json.loads(step.element).get('xpath'), 'completed': False} for i, step in enumerate(steps)]

def mark_step_completed(journey_steps, current_url, xpath):
    for step in journey_steps:
        if step['url'] == current_url and xpath.strip() == step['xpath'].strip():
            step['completed'] = True
            break
    session['journey_steps'] = journey_steps

def complete_journey(ongoing_journey):
    ongoing_journey.status = "COMPLETED"
    ongoing_journey.end_time = datetime.utcnow()
    db.session.commit()

def insert_event_and_update_journey(session_id, event_type, current_url, page_title, element, person_uuid, ongoing_journey=None, new_journey=None):
    element_str = json.dumps(element) if isinstance(element, dict) else element
    event = Event(
        session_id=session_id,
        event_type=event_type,
        url=current_url,
        page_title=page_title,
        element=element_str,
        customer_journey_id=(ongoing_journey.id if ongoing_journey else new_journey.id),
        timestamp=datetime.utcnow(),
        person_id=person_uuid
    )
    db.session.add(event)

    if ongoing_journey:
        ongoing_journey.updatedAt = datetime.utcnow()
    elif new_journey:
        new_journey.updatedAt = datetime.utcnow()

    db.session.commit()
    return event

@event_blueprint.route("/track", methods=["POST"])
def track_event():
    data = request.get_json()
    person_id = data.get("uuid")
    session_id = data.get("sessionId")
    current_url = data.get("url")
    page_title = data.get("pageTitle")
    event_type = data.get("eventType")
    element = data.get("element")
    xpath = element.get("xpath") if element else None

    person, customer_session = fetch_person_and_session(person_id, session_id)
    if not person or not customer_session:
        return jsonify({"error": "Person or customer_session not found"}), 404

    # 1) Check for an ongoing journey for this user
    ongoing_journey = CustomerJourney.query.filter_by(person_id=person.uuid, status="IN_PROGRESS").first()
    if ongoing_journey:
        return handle_ongoing_journey(ongoing_journey, session_id, event_type, current_url, page_title, element, person.uuid)

    # 2) If no ongoing journey, check if there's a matching active journey
    active_journeys = Journey.query.filter_by(status=JourneyLiveStatus.ACTIVE).all()

    for journey in active_journeys:
        first_step = json.loads(journey.first_step)  # Parse firstStep JSON

        # Check if current event matches the journey's first step
        if first_step.get("url") == current_url and first_step.get("elementDetails", {}).get("xpath") == xpath:
            return start_new_journey(session_id, event_type, current_url, page_title, element, person.uuid, journey.id)

    # If no match is found, return "not tracked" response
    return jsonify({"status": "No journey found for this URL and XPath. Event not tracked."}), 200