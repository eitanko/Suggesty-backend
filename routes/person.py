from flask import Blueprint, request, jsonify
from db import db
from models.customer_journey import Person, CustomerSession
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timedelta

SESSION_TIMEOUT_MINUTES = 1  # Example session timeout duration

person_blueprint = Blueprint("person", __name__)

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

    person = None
    if person_id:
        person = Person.query.filter(Person.uuid == person_id).first()
    if not person:
        # Create a new Person with a UUID (anonymous)
        person = Person()
        db.session.add(person)
        db.session.commit()

    # Check for an existing session
    latest_session = CustomerSession.query.filter_by(person_id=person.uuid).order_by(CustomerSession.created_at.desc()).first()

    if latest_session:
        session_age = datetime.utcnow() - latest_session.created_at
        if session_age < timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            # If session is still valid, return the existing session ID
            return jsonify({
                "personId": person.uuid,
                "sessionId": latest_session.session_id
            }), 200

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

    return jsonify({
        "personId": person.uuid,
        "sessionId": new_session.session_id
    }), 201
