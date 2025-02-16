from flask import Blueprint, request, jsonify
from db import db
from models import Person, CustomerSession
import uuid
from datetime import datetime, timedelta

SESSION_TIMEOUT_MINUTES = 30  # Example session timeout duration

person_blueprint = Blueprint("person", __name__)

# Helper function to check if UUID is valid
def is_valid_uuid(uuid_str):
    try:
        uuid.UUID(uuid_str)  # Try to create a UUID object from the string
        return True
    except ValueError:
        return False
    Z
@person_blueprint.route("/register", methods=["POST"])
def register_or_create_session():
    """
    Registers an anonymous user if they do not exist, or creates a new session for an existing user.
    If a valid session exists, it is returned instead.

    Request Body:
    - personId (str, optional): The unique identifier for the user (if known).
    - ipAddress (str, optional): The user's IP address.
    - userAgent (str, optional): The user agent string.

    Response:
    - JSON containing the Person ID and active Session ID.
    """

    data = request.get_json()
    person_id = data.get("uuid")  # Sent by the client if the user already exists

    print(f"🔍 Received request: {data}")

    person = None
    if person_id:
        if not is_valid_uuid(person_id):
            print(f"❌ Invalid UUID format: {person_id}")
            return jsonify({"error": "Invalid UUID format"}), 400
        print(f"🔎 Searching for existing person with UUID: {person_id}")

        person = Person.query.filter(Person.uuid == person_id).first()

    if not person:
        print("🆕 No existing person found, creating new person...")
        person = Person()
        db.session.add(person)
        db.session.commit()
        print(f"✅ New person created with UUID: {person.uuid}")

    # Check for an existing session
    print(f"🔍 Checking for existing session for person UUID: {person.uuid}")
    latest_session = CustomerSession.query.filter_by(person_id=person.uuid).order_by(CustomerSession.created_at.desc()).first()

    if latest_session:
        session_age = datetime.utcnow() - latest_session.created_at
        print(f"⏳ Existing session found: {latest_session.session_id}, Age: {session_age}")

        if session_age < timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            print("✅ Session is still valid, returning existing session.")
            return jsonify({
                "personId": person.uuid,
                "sessionId": latest_session.session_id
            }), 200
        else:
            print("⚠️ Session expired, creating a new session.")

    # If no valid session exists, create a new one
    new_session = CustomerSession(
        session_id=str(uuid.uuid4()),
        ip_address=data.get("ipAddress"),
        user_agent=data.get("userAgent"),
        api_key=data.get("apiKey"),
        person_id=person.uuid,
        created_at=datetime.utcnow()
    )
    db.session.add(new_session)
    db.session.commit()

    print(f"✅ New session created with ID: {new_session.session_id} for person {person.uuid}")

    return jsonify({
        "personId": person.uuid,
        "sessionId": new_session.session_id
    }), 201
