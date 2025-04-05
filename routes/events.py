from flask import Flask, request, jsonify, Blueprint
from db import db
from models.customer_journey import RawEvent

events_blueprint = Blueprint('events', __name__)

@events_blueprint.route("/", methods=["POST"])
def receive_posthog_event():
    # Get the JSON data from the request
    data = request.get_json()
    elements_chain = data.get("elements_chain")
    distinct_id = data.get("distinct_id"),

    # Check if the event contains the admin attribute
    if "attr__data-is-admin" in elements_chain and "true" in elements_chain:
        print(f"Ignoring admin event from distinctId: {distinct_id}")
        return None  # Skip processing this event

    raw_event = RawEvent(
        id=data.get("uuid"),
        session_id=data.get("session_id"),
        distinct_id=distinct_id,
        event=data.get("event"),
        event_type=data.get("event_type"),
        pathname=data.get("pathname"),
        current_url=data.get("current_url"),
        elements_chain=elements_chain,
        timestamp=data.get("timestamp")
    )

    try:
        # Add the new event to the session
        db.session.add(raw_event)

        # Commit the transaction to the database
        db.session.commit()

        return jsonify({"status": "ok", "saved": 1}), 201
    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        print(f"Failed to save event: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500