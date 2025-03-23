from models.customer_journey import Person, CustomerJourney, JourneyStatusEnum, Event, Journey, Step, JourneyLiveStatus
from flask import Blueprint, request, jsonify, session
from db import db
from datetime import datetime
from utils import compare_elements
import json

# Create a Blueprint for events
posthog_events_blueprint = Blueprint('posthog_events', __name__)

def fetch_person(person_id):
    return Person.query.filter_by(uuid=person_id).first()

def fetch_ongoing_journeys(person_id):
    return CustomerJourney.query.filter_by(person_id=person_id, status=JourneyStatusEnum.IN_PROGRESS.value).all()

def fetch_journey_steps(journey_id):
    steps = Step.query.filter_by(journey_id=journey_id).order_by(Step.created_at).all()
    return [{'step_number': i+1, 'url': step.url, 'xpath': json.loads(step.element).get('xpath'), 'elements_chain': step.elements_chain.split(';')[0], 'completed': False} for i, step in enumerate(steps)]

def mark_step_completed(journey_steps, current_url, elements_chain):
    for step in journey_steps:
        if not step['completed'] and step['url'] == current_url and compare_elements(step['elements_chain'].split(';')[0], elements_chain):
            step['completed'] = True
            break
    return journey_steps

def complete_journey(ongoing_journey):
    ongoing_journey.status = JourneyStatusEnum.COMPLETED.value
    ongoing_journey.end_time = datetime.utcnow()
    db.session.commit()

def insert_event_and_update_journey(session_id, event_type, current_url, page_title, element, elements_chain, person_uuid, customer_journey_id):
    element_str = json.dumps(element) if isinstance(element, dict) else element
    event = Event(
        session_id=session_id,
        event_type=event_type,
        url=current_url,
        page_title=page_title,
        element=element_str,
        elements_chain=elements_chain,
        customer_journey_id=customer_journey_id,
        timestamp=datetime.utcnow(),
        person_id=person_uuid
    )
    db.session.add(event)
    CustomerJourney.query.filter_by(id=customer_journey_id).update({'updated_at': datetime.utcnow()})
    db.session.commit()
    return event

@posthog_events_blueprint.route("/", methods=["POST"])
def receive_event():
    """Receive PostHog events and insert them into the database."""
    event = request.json
    if not event:
        return jsonify({"error": "Invalid event data"}), 400

    elements_chain = event.get("elements_chain", "")
    if not elements_chain:
        print("No elements_chain found in event.")
        return jsonify({"status": "No elements_chain found in event."}), 200

    elements_chain = elements_chain.split(';')[0]
    session_id = event.get("session_id", "N/A")
    event_type = event.get("event_type", "N/A")
    current_url = event.get("current_url", "N/A")
    page_title = event.get("page_title", "N/A")
    element = event.get("elementDetails", {})
    person_id = event.get("uuid", "N/A")

    # 1) Check for ongoing journeys for this user
    ongoing_journeys = fetch_ongoing_journeys(person_id)

    if ongoing_journeys:
        results = []
        for ongoing_journey in ongoing_journeys:
            journey_steps = session.get(f'journey_steps_{ongoing_journey.id}', fetch_journey_steps(ongoing_journey.journey_id))
            updated_journey_steps = mark_step_completed(journey_steps, current_url, elements_chain)
            session[f'journey_steps_{ongoing_journey.id}'] = updated_journey_steps

            if all(step['completed'] for step in updated_journey_steps):
                complete_journey(ongoing_journey)
                insert_event_and_update_journey(session_id, event_type, current_url, page_title, element, elements_chain, person_id, ongoing_journey.id)
                results.append({"status": "Journey completed", "CJID": ongoing_journey.id})
                del session[f'journey_steps_{ongoing_journey.id}'] #remove completed session
            else:
                insert_event_and_update_journey(session_id, event_type, current_url, page_title, element, elements_chain, person_id, ongoing_journey.id)
                results.append({"status": "Event tracked", "CJID": ongoing_journey.id})
        return jsonify(results), 201

    # 2) If no ongoing journey, check if there's a matching active journey
    active_journeys = Journey.query.with_entities(Journey.first_step, Journey.id).filter_by(status=JourneyLiveStatus.ACTIVE).all()

    new_journeys = [] # store the new journeys
    for journey in active_journeys:
        first_step = json.loads(journey.first_step)

        if first_step.get("url") == current_url and first_step.get("elementsChain") and compare_elements(first_step.get("elementsChain").split(';')[0], elements_chain):
            new_journey = CustomerJourney(
                session_id=session_id,
                journey_id=journey.id,
                person_id=person_id,
                status=JourneyStatusEnum.IN_PROGRESS.value,
            )
            db.session.add(new_journey)
            db.session.commit()

            journey_steps = fetch_journey_steps(journey.id)
            updated_journey_steps = mark_step_completed(journey_steps, current_url, elements_chain)
            session[f'journey_steps_{new_journey.id}'] = updated_journey_steps

            insert_event_and_update_journey(session_id, event_type, current_url, page_title, element, elements_chain, person_id, new_journey.id)
            new_journeys.append({"status": "New journey started and event tracked", "CJID": new_journey.id})

    if new_journeys:
        return jsonify(new_journeys), 201

    # If no match is found, return "not tracked" response
    return jsonify({"status": "No journey found for this URL and XPath. Event not tracked."}), 200
