from flask import request, jsonify, Blueprint
import psycopg2
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO)

ph_events_blueprint = Blueprint("paths", __name__)

def save_event(event_data):
    """Save the event to PostgreSQL"""
    print(event_data)
    return

@ph_events_blueprint.route("", methods=["POST"])
def receive_event():
    """Receive PostHog events"""
    event = request.json
    if not event:
        return jsonify({"error": "Invalid event data"}), 400

    logging.info("Received event: %s", event)

    print("Received Event:", event)
    # save_event(event)

    return jsonify({"message": "Event received"}), 200
