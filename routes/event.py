# routes/event.py
from models.event import Event
from flask import Blueprint, request, jsonify
# from config import Config  # Import the centralized configuration
from db import db

# Create a Blueprint for events
event_blueprint = Blueprint('event', __name__)


# Route to handle event POST requests
@event_blueprint.route('/', methods=['POST', 'OPTIONS'])
def create_event():
    # Get the event data from the incoming JSON request
    data = request.json
    print(data)

    # Extract the event fields from the request data
    session_id = data.get("sessionId")
    event_type = data.get("eventType")
    url = data.get("url")
    element = data.get("element")

    # Validate required fields
    if not all([session_id, event_type, url, element]):
        return jsonify({"error": "Missing required fields"}), 400

    # Create and save new event
    new_event = Event(
        session_id=session_id,
        event_type=event_type,
        url=url,
        element=element
    )
    db.session.add(new_event)
    db.session.commit()

    return jsonify({"message": "Event created successfully"}), 201

    # except Exception as e:
    #     return jsonify({"error": "An error occurred", "details": str(e)}), 500

