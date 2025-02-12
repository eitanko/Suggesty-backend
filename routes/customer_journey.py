from flask import Blueprint, request, jsonify
from db import db
from models.customer_journey import CustomerJourney, Person, CustomerSession
import uuid

customer_journey_blueprint = Blueprint("customer_journey", __name__)


@customer_journey_blueprint.route("/init", methods=["POST"])
def init_journey():
    """
    Endpoint: /init

    Description:
    This endpoint initializes a new customer journey. It performs the following actions:

    1. Generates a unique user ID if one does not exist and stores it in the user's browser (local storage).
    2. Creates a new record in the `Person` table (optional email and name for GDPR compliance).
    3. Creates a new session in the `CustomerSession` table, storing session details like IP address and user agent.
    4. Creates a new entry in the `CustomerJourney` table, marking the journey as "in-progress" with a provided `journeyId`.
    5. Returns the generated user ID for client-side storage.

    Method: POST
    Request Body:
    {
        "journeyId": int,  # Required, the ID of the journey being started
        "email": string,    # Optional, user email (for non-anonymous users)
        "name": string      # Optional, user name (for non-anonymous users)
    }

    Response:
    {
        "message":              "Customer journey initialized"
        "userId": int,          # Unique user ID for local storage
        "sessionId": string     # Unique session ID
        "CJID": int             # the customer journey ID
    }
    """
    data = request.get_json()

    journey_id = data.get("journeyId")
    email = data.get("email")  # Optional
    name = data.get("name")  # Optional
    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent")

    if not journey_id:
        return jsonify({"error": "Journey ID is required"}), 400

    # Generate unique user ID if not provided
    user_id = data.get("userId") or str(uuid.uuid4())

    # Check if the user already exists
    person = Person.query.filter_by(email=email).first() if email else None

    if not person:
        person = Person(name=name, email=email)
        db.session.add(person)
        db.session.commit()  # Get generated ID

    # Create a new session
    session = CustomerSession(
        session_id=str(uuid.uuid4()),
        ip_address=ip_address,
        user_agent=user_agent,
        api_key="some-api-key",  # Placeholder
        person_id=person.id
    )
    db.session.add(session)

    # Create a new journey entry
    customer_journey = CustomerJourney(
        user_id=person.id,
        journey_id=journey_id
    )
    db.session.add(customer_journey)

    try:
        db.session.commit()
        return jsonify({
            "message": "Customer journey initialized",
            "userId": person.id,  # Return the stored user ID for local storage
            "sessionId": session.session_id,
            "CJID": customer_journey.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to initialize journey", "message": str(e)}), 500
