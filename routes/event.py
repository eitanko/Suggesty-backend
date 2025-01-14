# routes/event.py
from flask import Blueprint, request, jsonify
#from models.event import Event
from flask import Blueprint, request, jsonify
import boto3
import base64
from uuid import uuid4
from config import Config  # Import the centralized configuration
from db import db



# Create a Blueprint for events
event_blueprint = Blueprint('event', __name__)


# Route to handle event POST requests
@event_blueprint.route('/', methods=['POST', 'OPTIONS'])
def log_event():
    # Get the event data from the incoming JSON request
    data = request.get_json()

    # Extract the event fields from the request data
    event_type = data.get('eventType')
    element_id = data.get('elementId')
    timestamp = data.get('timestamp')

    if not all([event_type, element_id, timestamp]):
        return jsonify({"error": "Missing required fields"}), 400

    # Create an Event instance (you can later save it to a database or process it further)
    #event = Event(event_type, element_id, timestamp)

    # Optionally, log the event (e.g., print it or save it to a DB)
    #print("Received Event:", event)

    # Respond with a success message
    return jsonify({"message": "Event received successfully!"}), 200
