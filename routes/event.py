from models.customer_journey import Event

from flask import Blueprint, request, jsonify
from db import db

# Create a Blueprint for events
event_blueprint = Blueprint('event', __name__)


# 🔹 POST: Create a new event in the system
@event_blueprint.route('/', methods=['POST', 'OPTIONS'])
def create_event():
    """
    Create a new event for a user session. This API endpoint accepts event data in the
    form of a JSON object and saves the event to the database.

    Request Body:
    - sessionId (str): The session identifier where the event occurred.
    - eventType (str): The type of event (e.g., click, scroll, etc.).
    - url (str): The URL where the event occurred.
    - element (str): The UI element associated with the event (e.g., button, link, etc.).
    - customerJourneyId (int): The ID of the associated customer journey. This links the event to a specific customer journey.

    Response:
    - 201 Created: Event successfully recorded.
    - 400 Bad Request: Missing required parameters or invalid data format.
    - 500 Internal Server Error: Database error or unexpected failure.

    Example Request:
    ```
    {
        "sessionId": "123e4567-e89b-12d3-a456-426614174000",
        "eventType": "click",
        "url": "https://example.com/page",
        "element": "#submit-button",
        "customerJourneyId": 42
    }
    ```

    Example Response:
    ```
    {
        "message": "Event created successfully",
        "eventId": 101
    }
    ```
    """

    # Get the event data from the incoming JSON request
    data = request.json

    # Extract the event fields from the request data
    session_id = data.get("sessionId")
    event_type = data.get("eventType")
    url = data.get("url")
    element = data.get("element")
    customer_journey_id = data.get("customerJourneyId")

    # Validate required fields
    if not all([session_id, event_type, url, element]):
        return jsonify({"error": "Missing required fields"}), 400

    # Create and save new event
    new_event = Event(
        session_id=session_id,
        event_type=event_type,
        url=url,
        element=element,
        customer_journey_id = customer_journey_id

    )
    db.session.add(new_event)
    db.session.commit()

    return jsonify({"message": "Event created successfully"}), 201